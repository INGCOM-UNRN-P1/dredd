"""Targets del docente (`dredd.mk`) en la corrección de una práctica de plantilla-TP (Ola 30).

deckard (`deckard guide practica`) deja, del lado del docente, una carpeta con `dredd.mk`
(targets `dredd-…`), `.dredd/` (pruebas ocultas) y `targets.json` (qué corre cada target, en
qué ejercicios, qué produce, su peso y si el alumno lo ve). La regla de la actividad en
`dredd.yaml` la nombra en `targets_docente`. Al corregir:

1. **Protección**: si la entrega trae su propio `dredd.mk` o `.dredd/`, se descartan, y un
   target `dredd-…` definido en un Makefile o `local.mk` de la entrega queda como alerta (el del
   docente lo pisa, porque `dredd.mk` se incluye al final).
2. Se copian `dredd.mk` y `.dredd/` a la raíz, se compilan las librerías (`make librerias`) y
   se corre cada target en cada ejercicio declarado (`make -C ejercicios/<id> dredd-…`), con
   tiempo máximo.
3. Se vuelve a dejar la entrega como estaba (se quitan `dredd.mk` y `.dredd/`).

El resultado va al informe (`targets_docente.md`) y a la nota: los pesos son porcentajes de la
nota de pruebas (`aplicar_a_nota`).
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

_TARGET_DEL_ALUMNO = re.compile(r"^(dredd-[\w-]+)\s*:", re.MULTILINE)
_MAX_SALIDA = 4000


@dataclass
class ResultadoTarget:
    target: str
    ejercicio: str
    aprobado: bool
    codigo: Optional[int]
    salida: str = ""
    datos: Optional[Any] = None      # JSON o Markdown que produjo, si lo declara
    peso: float = 0.0
    visible: bool = False
    descripcion: str = ""


@dataclass
class CorridaTargets:
    resultados: List[ResultadoTarget] = field(default_factory=list)
    alertas: List[str] = field(default_factory=list)
    error: Optional[str] = None

    def puntaje(self) -> Optional[float]:
        """Fracción ponderada (0 a 1) de targets aprobados; None si no hay pesos."""
        por_target: Dict[str, List[ResultadoTarget]] = {}
        for r in self.resultados:
            por_target.setdefault(r.target, []).append(r)
        total = sum(rs[0].peso for rs in por_target.values())
        if total <= 0:
            return None
        logrado = sum(rs[0].peso * sum(r.aprobado for r in rs) / len(rs) for rs in por_target.values())
        return logrado / total

    def peso_total(self) -> float:
        return sum({r.target: r.peso for r in self.resultados}.values())

    def to_dict(self) -> Dict[str, Any]:
        return {"resultados": [asdict(r) for r in self.resultados], "alertas": self.alertas,
                "error": self.error, "puntaje": self.puntaje(), "peso_total": self.peso_total()}


def cargar(carpeta: Path) -> Dict[str, Any]:
    """`targets.json` de la carpeta que generó deckard; ValueError si falta algo."""
    if not (carpeta / "dredd.mk").is_file() or not (carpeta / "targets.json").is_file():
        raise ValueError(f"{carpeta}: falta dredd.mk o targets.json (generalos con `deckard guide practica`)")
    return json.loads((carpeta / "targets.json").read_text(encoding="utf-8"))


def verificar(carpeta: Path) -> List[str]:
    """Problemas de la carpeta de targets: cada target declarado tiene que estar en dredd.mk."""
    try:
        descripcion = cargar(carpeta)
    except (ValueError, json.JSONDecodeError) as exc:
        return [str(exc)]
    mk = (carpeta / "dredd.mk").read_text(encoding="utf-8")
    definidos = set(re.findall(r"^(dredd-[\w-]+):", mk, re.MULTILINE))
    return [f"{carpeta}: el target {t['target']} está en targets.json pero no en dredd.mk"
            for t in descripcion.get("targets", []) if t.get("target") not in definidos]


def proteger(entrega: Path) -> List[str]:
    """Descarta el dredd.mk o .dredd/ propios de la entrega y avisa de targets dredd-… del alumno."""
    alertas = []
    for nombre in ("dredd.mk", ".dredd"):
        propio = entrega / nombre
        if propio.exists():
            alertas.append(f"la entrega trae su propio {nombre}: se descartó (la corrección usa el del docente)")
            shutil.rmtree(propio) if propio.is_dir() else propio.unlink()
    for mk in sorted(list(entrega.rglob("Makefile")) + list(entrega.rglob("*.mk"))):
        if ".git" in mk.parts:
            continue
        try:
            texto = mk.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for target in sorted(set(_TARGET_DEL_ALUMNO.findall(texto))):
            alertas.append(f"{mk.relative_to(entrega)} define {target}: los targets dredd-… son de la cátedra "
                           "(en la corrección vale el del docente)")
    return alertas


def _leer_producido(dir_ej: Path, produce: str, archivo: Optional[str]) -> Any:
    if produce == "codigo" or not archivo:
        return None
    ruta = dir_ej / archivo
    if not ruta.is_file():
        return None
    texto = ruta.read_text(encoding="utf-8", errors="replace")
    if produce == "json":
        try:
            return json.loads(texto)
        except json.JSONDecodeError:
            return None
    return texto[:_MAX_SALIDA]


def correr(entrega: Path, carpeta: Path, timeout: int = 120) -> CorridaTargets:
    """Protege el gancho, corre los targets declarados y deja la entrega como estaba."""
    corrida = CorridaTargets(alertas=proteger(entrega))
    try:
        descripcion = cargar(carpeta)
    except (ValueError, json.JSONDecodeError) as exc:
        corrida.error = str(exc)
        return corrida
    shutil.copy2(carpeta / "dredd.mk", entrega / "dredd.mk")
    if (carpeta / ".dredd").is_dir():
        shutil.copytree(carpeta / ".dredd", entrega / ".dredd", dirs_exist_ok=True)
    try:
        if (entrega / "Makefile").is_file():
            subprocess.run(["make", "-s", "-k", "librerias"], cwd=entrega, capture_output=True, text=True,
                           timeout=timeout)
        for t in descripcion.get("targets", []):
            for eid in t.get("ejercicios", []):
                dir_ej = entrega / "ejercicios" / eid
                if not (dir_ej / "Makefile").is_file():
                    corrida.resultados.append(ResultadoTarget(t["target"], eid, False, None, "el ejercicio no está en la entrega",
                                                              peso=float(t.get("peso", 0)), visible=bool(t.get("visible")),
                                                              descripcion=t.get("descripcion", "")))
                    continue
                try:
                    res = subprocess.run(["make", "-s", "-C", str(dir_ej), t["target"]], capture_output=True, text=True,
                                         timeout=timeout)
                    codigo: Optional[int] = res.returncode
                    salida = (res.stdout + res.stderr)[-_MAX_SALIDA:]
                except subprocess.TimeoutExpired:
                    codigo, salida = None, f"tiempo agotado ({timeout} s)"
                corrida.resultados.append(ResultadoTarget(
                    t["target"], eid, codigo == 0, codigo, salida,
                    _leer_producido(dir_ej, t.get("produce", "codigo"), t.get("archivo")),
                    float(t.get("peso", 0)), bool(t.get("visible")), t.get("descripcion", "")))
    finally:
        (entrega / "dredd.mk").unlink(missing_ok=True)
        shutil.rmtree(entrega / ".dredd", ignore_errors=True)
    return corrida


def seccion_markdown(datos: Dict[str, Any], para_alumno: bool = False) -> str:
    """Sección del informe; con `para_alumno`, sólo los targets visibles y sin la salida."""
    resultados = [r for r in datos.get("resultados", []) if r.get("visible") or not para_alumno]
    estado = "ok" if all(r["aprobado"] for r in resultados) and not datos.get("alertas") else "fail"
    lineas = [f"<!-- dredd-section: targets_docente, tool=dredd, version=1.0.0, status={estado} -->",
              "## Revisiones de la cátedra", ""]
    if datos.get("error"):
        lineas += [f"> [!WARNING]\n> No se pudieron correr: {datos['error']}", ""]
    if datos.get("alertas"):
        lineas += ["> [!CAUTION]", "> **El gancho de la corrección fue modificado:**"]
        lineas += [f"> - {a}" for a in datos["alertas"]] + [""]
    if resultados:
        lineas += ["| Revisión | Ejercicio | Resultado | Peso |", "| :-- | :-- | :-: | :-: |"]
        for r in resultados:
            lineas.append(f"| {r.get('descripcion') or r['target']} | `{r['ejercicio']}` | "
                          f"{'✓' if r['aprobado'] else '✗'} | {r.get('peso', 0):g} % |")
        lineas.append("")
        if datos.get("puntaje") is not None and not para_alumno:
            lineas += [f"Puntaje ponderado de las revisiones: {100 * datos['puntaje']:.0f} % "
                       f"(pesan {datos.get('peso_total', 0):g} % de la nota de pruebas).", ""]
        if not para_alumno:
            for r in resultados:
                if not r["aprobado"] and r.get("salida"):
                    lineas += [f"<details><summary>{r['target']} en {r['ejercicio']}</summary>", "",
                               "```text", r["salida"].strip(), "```", "", "</details>", ""]
    return "\n".join(lineas)


def aplicar_a_nota(nota_tests: Optional[float], resultado_targets: Optional[Dict[str, Any]]) -> Optional[float]:
    """Nota de pruebas (0-10) con los targets: sus pesos son porcentajes de esa nota."""
    if not resultado_targets or resultado_targets.get("puntaje") is None:
        return nota_tests
    peso = min(100.0, float(resultado_targets.get("peso_total") or 0)) / 100
    base = nota_tests if nota_tests is not None else 0.0
    return round(base * (1 - peso) + 10.0 * float(resultado_targets["puntaje"]) * peso, 2)
