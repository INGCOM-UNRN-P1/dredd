"""Módulo de limpieza de artefactos de evaluación previa (carpetas rNi e informes generados)."""

from __future__ import annotations

import os
from pathlib import Path
import re
import shutil
from typing import Any, Dict, List, Optional, Set, Tuple


# Carpetas de revisiones internas generadas por las herramientas (r1i, r2i, r10i, etc.)
PATRON_DIR_RNI = re.compile(r"^r\d+i$", re.IGNORECASE)

# Informes consolidados y exportaciones generadas por Dredd
PATRON_ARCHIVO_INFORME = re.compile(
    r"^(?:.+_r\d+|informe(?:_.*)?|alumno_r\d+.*|feedback_.*|devolucion_.*)\.(?:md|html|pdf)$",
    re.IGNORECASE,
)

# Archivos protegidos que jamás deben ser eliminados bajo ninguna circunstancia
ARCHIVOS_PROTEGIDOS: Set[str] = {
    "readme.md",
    "enunciado.md",
    "makefile",
    "cmakelists.txt",
    "ejercicio.yaml",
    "guia.yaml",
    "dredd.yaml",
    "config.yaml",
}


def es_directorio_rni(path: Path) -> bool:
    """Indica si la ruta corresponde a un directorio intermedio de herramientas rNi."""
    return path.is_dir() and bool(PATRON_DIR_RNI.match(path.name))


def es_archivo_informe(path: Path) -> bool:
    """Indica si el archivo corresponde a un reporte generado por Dredd."""
    if not path.is_file():
        return False
    nombre_lower = path.name.lower()
    if nombre_lower in ARCHIVOS_PROTEGIDOS:
        return False
    if nombre_lower.endswith((".c", ".h", ".yaml", ".yml", ".json", ".in", ".out")):
        return False
    return bool(PATRON_ARCHIVO_INFORME.match(path.name))


def _obtener_tamano_directorio(dir_path: Path) -> int:
    """Calcula el tamaño en bytes de un directorio."""
    total = 0
    try:
        for root, _, files in os.walk(dir_path):
            for f in files:
                fp = os.path.join(root, f)
                if not os.path.islink(fp):
                    total += os.path.getsize(fp)
    except Exception:
        pass
    return total


def limpiar_evaluaciones_estudiante(
    student_dir: Path,
    dry_run: bool = False,
    limpiar_rni: bool = True,
    limpiar_informes: bool = True,
) -> Dict[str, Any]:
    """Limpia carpetas rNi e informes generados dentro de la carpeta de un estudiante."""
    rni_encontrados: List[Path] = []
    informes_encontrados: List[Path] = []
    bytes_liberados = 0

    if not student_dir.is_dir():
        return {
            "rni": [],
            "informes": [],
            "bytes": 0,
        }

    # 1. Buscar subdirectorios rNi (y también dentro de rN o rN_f si estuviera anidado)
    if limpiar_rni:
        for item in list(student_dir.iterdir()):
            if es_directorio_rni(item):
                rni_encontrados.append(item)
            elif item.is_dir() and re.match(r"^r\d+(?:_f)?$", item.name, re.IGNORECASE):
                for sub in item.iterdir():
                    if es_directorio_rni(sub):
                        rni_encontrados.append(sub)

    # 2. Buscar archivos de informe en student_dir y en rN/rN_f
    if limpiar_informes:
        for item in list(student_dir.iterdir()):
            if es_archivo_informe(item):
                informes_encontrados.append(item)
            elif item.is_dir() and re.match(r"^r\d+(?:_f)?$", item.name, re.IGNORECASE):
                for sub in item.iterdir():
                    if es_archivo_informe(sub):
                        informes_encontrados.append(sub)

    # 3. Eliminar (si no es dry_run) y calcular espacio
    for d in rni_encontrados:
        bytes_liberados += _obtener_tamano_directorio(d)
        if not dry_run:
            shutil.rmtree(d, ignore_errors=True)

    for f in informes_encontrados:
        try:
            bytes_liberados += f.stat().st_size
            if not dry_run:
                f.unlink(missing_ok=True)
        except Exception:
            pass

    return {
        "rni": rni_encontrados,
        "informes": informes_encontrados,
        "bytes": bytes_liberados,
    }


def limpiar_evaluaciones(
    base_dir: Path,
    student: Optional[str] = None,
    dry_run: bool = False,
    limpiar_rni: bool = True,
    limpiar_informes: bool = True,
) -> Dict[str, Any]:
    """Limpia evaluaciones anteriores en un directorio de entregas o para un estudiante específico.

    Retorna un diccionario consolidado con estadísticas y rutas eliminadas.
    """
    base_dir = Path(base_dir).resolve()
    if not base_dir.exists():
        return {
            "estudiantes_afectados": 0,
            "directorios_rni": [],
            "informes": [],
            "bytes_liberados": 0,
            "detalles": {},
        }

    # Identificar carpetas de estudiantes
    directorios_estudiantes: List[Path] = []

    # Caso A: base_dir es directamente la carpeta de un estudiante
    if student is None and any(es_directorio_rni(p) or es_archivo_informe(p) for p in base_dir.iterdir() if p.is_file() or p.is_dir()):
        # Puede ser la carpeta de un único estudiante
        directorios_estudiantes.append(base_dir)
    elif student is not None:
        cand = base_dir / student
        if cand.is_dir():
            directorios_estudiantes.append(cand)
        elif base_dir.name == student:
            directorios_estudiantes.append(base_dir)
    else:
        # Caso B: base_dir contiene carpetas de estudiantes
        for sub in sorted(base_dir.iterdir()):
            if sub.is_dir() and not sub.name.startswith((".", "_")):
                directorios_estudiantes.append(sub)

    total_rni: List[Path] = []
    total_informes: List[Path] = []
    total_bytes = 0
    detalles: Dict[str, Dict[str, Any]] = {}
    estudiantes_con_limpieza = 0

    for s_dir in directorios_estudiantes:
        s_nombre = s_dir.name
        res = limpiar_evaluaciones_estudiante(
            student_dir=s_dir,
            dry_run=dry_run,
            limpiar_rni=limpiar_rni,
            limpiar_informes=limpiar_informes,
        )
        if res["rni"] or res["informes"]:
            estudiantes_con_limpieza += 1
            total_rni.extend(res["rni"])
            total_informes.extend(res["informes"])
            total_bytes += res["bytes"]
            detalles[s_nombre] = res

    return {
        "estudiantes_afectados": estudiantes_con_limpieza,
        "directorios_rni": total_rni,
        "informes": total_informes,
        "bytes_liberados": total_bytes,
        "detalles": detalles,
    }
