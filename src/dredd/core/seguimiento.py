"""Planilla de seguimiento de una cohorte de GitHub Classroom (Ola 25).

Recorre una carpeta con un repositorio clonado por alumno (lo que hace sulaco `cohorte.yml`),
corre `ripley check --json` en cada uno y consolida:

- el estado de cada entrega (aprobada, con errores, no compila, sin entrega) con el mismo
  veredicto de perfil que ripley (`strict`, `relaxed`, `exam`);
- las observaciones más frecuentes de la cohorte (en cuántos alumnos aparece cada regla), con
  el enlace al apunte, para decidir qué reforzar en clase;
- los tiempos: commits del alumno (sin los del bot de Classroom), primer y último commit y, con
  una fecha límite, cuántas horas de atraso. La fecha es la del commit: la puede fijar el alumno,
  así que el atraso es orientativo (el registro de push lo tiene GitHub, no el repositorio).

Salida en CSV (para la planilla), Markdown (resumen del job) y JSON.
"""

from __future__ import annotations

import csv
import json
import subprocess
from collections import Counter
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

ESTADOS = ("aprobada", "con errores", "no compila", "sin entrega", "error al analizar")


@dataclass
class EntregaCohorte:
    alumno: str
    repo: str
    estado: str = "sin entrega"
    compila: Optional[bool] = None
    errores: int = 0
    advertencias: int = 0
    estilo: int = 0
    pruebas_ok: int = 0
    pruebas_total: int = 0
    commits: int = 0
    primer_commit: Optional[str] = None
    ultimo_commit: Optional[str] = None
    atraso_horas: Optional[float] = None
    reglas: List[str] = field(default_factory=list)
    detalle: str = ""


def _commits_del_alumno(repo: Path) -> List[datetime]:
    """Fechas de los commits que no son de un bot (el de Classroom crea el primero)."""
    res = subprocess.run(["git", "-C", str(repo), "log", "--format=%an%x09%cI"], capture_output=True, text=True)
    fechas = []
    for linea in res.stdout.splitlines():
        autor, _, fecha = linea.partition("\t")
        if autor.endswith("[bot]") or not fecha:
            continue
        try:
            fechas.append(datetime.fromisoformat(fecha))
        except ValueError:
            continue
    return sorted(fechas)


def veredicto(datos: Dict[str, Any], perfil: str = "strict") -> bool:
    """True si la entrega tiene errores, con el criterio de `ripley check` (tiene_errores)."""
    metricas = datos.get("metrics", {}) or {}
    errores = not (datos.get("compilation", {}) or {}).get("success", False) or (
        perfil != "relaxed" and (metricas.get("ast_errors_count", 0) > 0 or (datos.get("tests", {}) or {}).get("failed", 0) > 0))
    if perfil == "exam":
        errores = errores or metricas.get("ast_findings_count", 0) > 0
    return bool(errores)


def analizar_repo(repo: Path, alumno: str, ruta: str, perfil: str, ripley: str,
                  fecha_limite: Optional[datetime] = None, timeout: int = 300) -> tuple:
    """(entrega, hallazgos del sobre común) de un repositorio."""
    entrega = EntregaCohorte(alumno=alumno, repo=repo.name)
    fechas = _commits_del_alumno(repo)
    entrega.commits = len(fechas)
    if fechas:
        entrega.primer_commit, entrega.ultimo_commit = fechas[0].isoformat(), fechas[-1].isoformat()
        if fecha_limite is not None:
            atraso = (fechas[-1] - fecha_limite).total_seconds() / 3600
            entrega.atraso_horas = round(atraso, 1) if atraso > 0 else 0.0
    objetivo = repo / ruta
    if not fechas or not objetivo.exists() or not any(objetivo.rglob("*.c") if objetivo.is_dir() else [objetivo]):
        entrega.estado = "sin entrega"
        return entrega, []
    try:
        res = subprocess.run([ripley, "check", ruta, "--json", "--exit-zero", "--profile", perfil],
                             cwd=str(repo), capture_output=True, text=True, timeout=timeout)
        datos = json.loads(res.stdout)
    except (subprocess.TimeoutExpired, ValueError, OSError) as e:
        entrega.estado, entrega.detalle = "error al analizar", str(e)[:200]
        return entrega, []
    hallazgos = datos.get("hallazgos", []) or []
    for h in hallazgos:
        sev = str(h.get("severidad", "")).lower()
        if sev == "error":
            entrega.errores += 1
        elif sev == "advertencia":
            entrega.advertencias += 1
        else:
            entrega.estilo += 1
    entrega.reglas = sorted({str(h.get("codigo")) for h in hallazgos if h.get("codigo")})
    pruebas = datos.get("tests", {}) or {}
    entrega.pruebas_ok, entrega.pruebas_total = int(pruebas.get("passed", 0)), int(pruebas.get("total", 0))
    entrega.compila = bool((datos.get("compilation", {}) or {}).get("success", False))
    if not entrega.compila:
        entrega.estado = "no compila"
    else:
        entrega.estado = "con errores" if veredicto(datos, perfil) else "aprobada"
    return entrega, hallazgos


def frecuentes(hallazgos_por_alumno: Dict[str, List[Dict[str, Any]]], limite: int = 10) -> List[Dict[str, Any]]:
    """Las reglas que aparecen en más alumnos (una vez por alumno), con mensaje y enlace."""
    alumnos: Counter = Counter()
    muestra: Dict[str, Dict[str, Any]] = {}
    for hallazgos in hallazgos_por_alumno.values():
        for codigo in {str(h.get("codigo")) for h in hallazgos if h.get("codigo")}:
            alumnos[codigo] += 1
        for h in hallazgos:
            muestra.setdefault(str(h.get("codigo")), h)
    return [{"codigo": c, "alumnos": n, "categoria": muestra[c].get("categoria"),
             "mensaje": muestra[c].get("mensaje"), "enlace": muestra[c].get("enlace")}
            for c, n in alumnos.most_common(limite)]


def analizar_cohorte(carpeta: Path, ruta: str = ".", perfil: str = "strict", prefijo: str = "",
                     fecha_limite: Optional[datetime] = None, ripley: str = "ripley") -> Dict[str, Any]:
    entregas: List[EntregaCohorte] = []
    hallazgos: Dict[str, List[Dict[str, Any]]] = {}
    for repo in sorted(p for p in carpeta.iterdir() if (p / ".git").exists()):
        alumno = repo.name[len(prefijo):] if prefijo and repo.name.startswith(prefijo) else repo.name
        entrega, propios = analizar_repo(repo, alumno.lstrip("-_"), ruta, perfil, ripley, fecha_limite)
        entregas.append(entrega)
        hallazgos[entrega.alumno] = propios
    estados = Counter(e.estado for e in entregas)
    return {
        "schema_version": "1.0.0",
        "generado": datetime.now().astimezone().isoformat(timespec="seconds"),
        "perfil": perfil,
        "fecha_limite": fecha_limite.isoformat() if fecha_limite else None,
        "totales": {estado: estados.get(estado, 0) for estado in ESTADOS} | {"alumnos": len(entregas)},
        "frecuentes": frecuentes(hallazgos),
        "entregas": [asdict(e) for e in entregas],
    }


_COLUMNAS = ["alumno", "repo", "estado", "compila", "errores", "advertencias", "estilo", "pruebas_ok",
             "pruebas_total", "commits", "primer_commit", "ultimo_commit", "atraso_horas", "reglas", "detalle"]


def escribir(informe: Dict[str, Any], salida: Path) -> Sequence[Path]:
    salida.mkdir(parents=True, exist_ok=True)
    rutas = [salida / "cohorte.csv", salida / "cohorte.md", salida / "cohorte.json"]
    with rutas[0].open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=_COLUMNAS)
        w.writeheader()
        for e in informe["entregas"]:
            w.writerow({**{k: e.get(k) for k in _COLUMNAS}, "reglas": " ".join(e.get("reglas", []))})
    rutas[1].write_text(markdown(informe), encoding="utf-8")
    rutas[2].write_text(json.dumps(informe, indent=2, ensure_ascii=False), encoding="utf-8")
    return rutas


def _celda(valor: Any) -> str:
    return "—" if valor in (None, "") else str(valor).replace("|", "\\|")


def markdown(informe: Dict[str, Any]) -> str:
    t = informe["totales"]
    lineas = ["# Seguimiento de la cohorte", "",
              f"{t['alumnos']} alumnos · perfil `{informe['perfil']}`"
              + (f" · fecha límite {informe['fecha_limite']}" if informe.get("fecha_limite") else ""), "",
              "| Aprobadas | Con errores | No compilan | Sin entrega | Error al analizar |",
              "| :-: | :-: | :-: | :-: | :-: |",
              f"| {t['aprobada']} | {t['con errores']} | {t['no compila']} | {t['sin entrega']} | {t['error al analizar']} |", ""]
    if informe["frecuentes"]:
        lineas += ["## Observaciones más frecuentes", "", "| Regla | Alumnos | Tema | Mensaje |", "| :-- | :-: | :-- | :-- |"]
        for f in informe["frecuentes"]:
            regla = f"[{f['codigo']}]({f['enlace']})" if f.get("enlace") else f"`{f['codigo']}`"
            lineas.append(f"| {regla} | {f['alumnos']} | {_celda(f.get('categoria'))} | {_celda(f.get('mensaje'))} |")
        lineas.append("")
    lineas += ["## Entregas", "", "| Alumno | Estado | Errores | Advertencias | Pruebas | Commits | Último commit | Atraso (h) |",
               "| :-- | :-- | :-: | :-: | :-: | :-: | :-- | :-: |"]
    for e in informe["entregas"]:
        pruebas = f"{e['pruebas_ok']}/{e['pruebas_total']}" if e["pruebas_total"] else "—"
        lineas.append(f"| {_celda(e['alumno'])} | {e['estado']} | {e['errores']} | {e['advertencias']} | {pruebas} | "
                      f"{e['commits']} | {_celda(e['ultimo_commit'])} | {_celda(e['atraso_horas'])} |")
    lineas += ["", "> El atraso sale de la fecha del último commit, que el alumno puede fijar: es orientativo."]
    return "\n".join(lineas) + "\n"
