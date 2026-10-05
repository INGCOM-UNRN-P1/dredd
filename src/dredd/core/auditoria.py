"""Registro de auditoría de cada corrección (revisión 07, dredd): con qué versión de cada
herramienta se evaluó una entrega.

Ante un reclamo hay que poder volver a correr la entrega con lo mismo. Junto a los informes de cada
revisión (`rNi/`) queda un `auditoria.json` con la fecha, la versión de dredd y de cada satélite
instalado y la de gcc; `dredd audit-versions` los lista y marca las entregas evaluadas con versiones
distintas de las del resto del curso.
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


def registrar(directorio: Path, alumno: str, actividad: str, revision: str,
              commit: Optional[str] = None) -> Path:
    datos = {
        "schema_version": "1.0.0",
        "fecha": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "actividad": actividad,
        "alumno": alumno,
        "revision": revision,
        "commit": commit,
        "versiones": versiones_del_ecosistema(),
    }
    directorio.mkdir(parents=True, exist_ok=True)
    destino = directorio / ARCHIVO
    destino.write_text(json.dumps(datos, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return destino


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
