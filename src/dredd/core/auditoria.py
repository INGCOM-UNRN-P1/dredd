"""Registro de auditoría de cada corrección (revisión 07, dredd): con qué versión de cada
herramienta se evaluó una entrega.

Ante un reclamo hay que poder volver a correr la entrega con lo mismo. Junto a los informes de cada
revisión (`rNi/`) queda un `auditoria.json` con la fecha, la versión de dredd y de cada satélite
instalado y la de gcc; `dredd audit-versions` los lista y marca las entregas evaluadas con versiones
distintas de las del resto del curso.

El mismo archivo es el cursor de las corridas masivas (Ola 8): `estado` pasa de `en_curso` a
`completa` cuando el informe quedó escrito (o a `error`), y `resultado` resume la compilación y las
pruebas. `dredd eval --resume` saltea las revisiones completas y `--failed-only` re-evalúa sólo las
que fallaron; `deckard exercise rubric --eval-results` calcula la nota con `resultado` y
`hallazgos.json`.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from collections import Counter
from datetime import datetime, timezone
from importlib import metadata
from pathlib import Path
from typing import Any, Dict, List, Optional

ARCHIVO = "auditoria.json"
HERRAMIENTAS = (
    "dredd", "ripley", "daedalus", "gaff", "hal", "tetsuo", "nostromo", "bishop", "spunkmeyer", "kaneda",
    "zhora", "motoko", "corbel", "weyl", "giger", "vassili", "vasquez", "holden", "tyrell", "drake", "ferro",
    "sebastian", "dietrich", "brett", "kane", "wierzbowski", "yutani",
)


def versiones_del_ecosistema() -> Dict[str, str]:
    versiones = {}
    for nombre in HERRAMIENTAS:
        try:
            versiones[nombre] = metadata.version(nombre)
        except metadata.PackageNotFoundError:
            continue
    gcc = shutil.which("gcc")
    if gcc:
        try:
            primera = subprocess.run([gcc, "--version"], capture_output=True, text=True, timeout=10).stdout.splitlines()
            versiones["gcc"] = primera[0].strip() if primera else "?"
        except (OSError, subprocess.SubprocessError):
            pass
    return versiones


ESTADOS = ("en_curso", "completa", "error")


def resultado_del_analisis(analysis: Dict[str, Any]) -> Dict[str, Any]:
    """La compilación y las pruebas del análisis de ripley, lo que hace falta para calificar."""
    tests = analysis.get("tests") or {}
    casos = [{"nombre": str(c.get("name") or ""), "aprobado": bool(c.get("passed")),
              "fuga_memoria": bool(c.get("memory_leak"))} for c in tests.get("cases") or []]
    return {
        "compilacion": bool((analysis.get("compilation") or {}).get("success")),
        "tests": {"aprobados": int(tests.get("passed") or 0), "total": int(tests.get("total") or 0), "casos": casos},
    }


def registrar(directorio: Path, alumno: str, actividad: str, revision: str,
              commit: Optional[str] = None, estado: str = "en_curso",
              resultado: Optional[Dict[str, Any]] = None, error: Optional[str] = None) -> Path:
    if estado not in ESTADOS:
        raise ValueError(f"estado desconocido: {estado}")
    datos: Dict[str, Any] = {
        "schema_version": "1.1.0",
        "fecha": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "actividad": actividad,
        "alumno": alumno,
        "revision": revision,
        "commit": commit,
        "estado": estado,
        "versiones": versiones_del_ecosistema(),
    }
    if resultado is not None:
        datos["resultado"] = resultado
    if error:
        datos["error"] = error
    directorio.mkdir(parents=True, exist_ok=True)
    destino = directorio / ARCHIVO
    destino.write_text(json.dumps(datos, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return destino


def leer(directorio: Path) -> Optional[Dict[str, Any]]:
    try:
        datos = json.loads((Path(directorio) / ARCHIVO).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return datos if isinstance(datos, dict) else None


def marcar(directorio: Path, estado: str) -> None:
    """Cambia el estado de la revisión ya registrada (sin volver a consultar las versiones)."""
    if estado not in ESTADOS:
        raise ValueError(f"estado desconocido: {estado}")
    datos = leer(directorio)
    if datos is None:
        return
    datos["estado"] = estado
    (Path(directorio) / ARCHIVO).write_text(json.dumps(datos, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def completa(directorio: Path, commit: Optional[str] = None) -> bool:
    """True si la revisión ya se evaluó entera (y, si se sabe, sobre el mismo commit)."""
    datos = leer(directorio)
    if not datos or datos.get("estado") != "completa":
        return False
    return not (commit and datos.get("commit") and datos["commit"] != commit)


def fallida(directorio: Path) -> Optional[bool]:
    """Si la revisión hay que volver a evaluarla: no terminó, no compiló o falló alguna prueba.
    None si el registro es anterior al cursor (sin `estado`) o no existe."""
    datos = leer(directorio)
    if not datos or "estado" not in datos:
        return None
    if datos["estado"] != "completa":
        return True
    resultado = datos.get("resultado") or {}
    tests = resultado.get("tests") or {}
    return (not resultado.get("compilacion", False)
            or int(tests.get("aprobados") or 0) < int(tests.get("total") or 0)
            or any(c.get("fuga_memoria") for c in tests.get("casos") or []))


def ultima_revision(directorio_alumno: Path) -> Optional[Path]:
    """El directorio intermedio (`rNi/` o `i_<hash>/`) de la última revisión registrada del alumno."""
    candidatos = []
    for archivo in Path(directorio_alumno).glob(f"*/{ARCHIVO}"):
        datos = leer(archivo.parent) or {}
        candidatos.append((str(datos.get("fecha") or ""), _numero(archivo.parent.name), archivo.parent))
    return max(candidatos)[2] if candidatos else None


def _numero(nombre: str) -> int:
    digitos = "".join(c for c in nombre if c.isdigit()) if nombre.startswith("r") else ""
    return int(digitos) if digitos else 0


def leer_registros(raiz: Path) -> List[Dict[str, Any]]:
    registros = []
    for archivo in sorted(Path(raiz).rglob(ARCHIVO)):
        try:
            datos = json.loads(archivo.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        datos["ruta"] = str(archivo)
        registros.append(datos)
    return registros


def versiones_distintas(registros: List[Dict[str, Any]]) -> Dict[str, Dict[str, str]]:
    """Por registro (ruta), las herramientas cuya versión difiere de la más usada en el curso."""
    mas_usada: Dict[str, str] = {}
    for herramienta in {h for r in registros for h in r.get("versiones", {})}:
        conteo = Counter(r["versiones"][herramienta] for r in registros if herramienta in r.get("versiones", {}))
        mas_usada[herramienta] = conteo.most_common(1)[0][0]
    distintas = {}
    for r in registros:
        dif = {h: v for h, v in r.get("versiones", {}).items() if v != mas_usada.get(h)}
        if dif:
            distintas[r["ruta"]] = dif
    return distintas
