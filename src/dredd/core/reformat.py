"""Reformateador de directorios de entrega para estructurar fuentes en rN_f (r1_f, r2_f, etc.)."""

from __future__ import annotations

from pathlib import Path
import re
import shutil
from typing import List, Optional, Set


SOURCE_EXTENSIONS = {".c", ".h", ".in", ".out", ".txt", ".dat", ".csv"}
IMPORTANT_FILENAMES = {"makefile", "cmakelists.txt", "casos.yaml", "tests.json"}
IGNORED_SUBDIRS = {"__macosx", ".git", ".idea", ".vscode", "__pycache__"}


def find_existing_revision_folders(student_dir: Path) -> List[tuple[int, Path]]:
    """Encuentra carpetas de revisión existentes (r1, r1_f, r2_f, etc.) ordenadas por número."""
    if not student_dir.is_dir():
        return []

    revs: List[tuple[int, Path]] = []
    for item in student_dir.iterdir():
        if not item.is_dir():
            continue
        m = re.match(r"^r(\d+)(?:_f)?$", item.name, re.IGNORECASE)
        if m:
            revs.append((int(m.group(1)), item))

    return sorted(revs, key=lambda x: x[0])


def reformat_submission_to_rn_f(
    student_dir: Path,
    target_version: Optional[int] = None,
) -> Path:
    """Reformatea el directorio de entrega del estudiante para que quede en rN_f (r1_f, r2_f, etc.).
    
    1. Renombra carpetas rN existentes a rN_f si no tenían el sufijo _f.
    2. Si hay archivos de fuentes o subcarpetas sueltas fuera de rN_f, los mueve/aplana dentro de rN_f.
    3. Devuelve la ruta absoluta al directorio rN_f activo.
    """
    student_dir = Path(student_dir).resolve()
    if not student_dir.is_dir():
        return student_dir

    # 1. Si ya existen carpetas rN sin _f, renombrarlas a rN_f
    for num, folder in find_existing_revision_folders(student_dir):
        if folder.name.lower() == f"r{num}":
            target_renamed = student_dir / f"r{num}_f"
            if not target_renamed.exists():
                folder.rename(target_renamed)

    existing_rf = find_existing_revision_folders(student_dir)

    # 2. Recolectar archivos sueltos fuera de cualquier carpeta r*_f o .git
    loose_items: List[Path] = []
    for item in student_dir.iterdir():
        if item.name.startswith(".") or item.name.endswith(".md") or item.name == ".metadata.db":
            continue
        # Omitir las carpetas de revisión r*_f ya creadas
        if item.is_dir() and re.match(r"^r\d+_f$", item.name, re.IGNORECASE):
            continue
        loose_items.append(item)

    # 3. Determinar el número de revisión N
    if target_version is not None:
        version_num = target_version
    elif existing_rf and not loose_items:
        # Ya está formateado, usar la última revisión existente
        return existing_rf[-1][1]
    elif existing_rf and loose_items:
        # Hay nueva entrega sobre una existente -> r{max + 1}_f
        version_num = existing_rf[-1][0] + 1
    else:
        # Primera entrega
        version_num = 1

    target_rf_dir = student_dir / f"r{version_num}_f"
    target_rf_dir.mkdir(parents=True, exist_ok=True)

    # 4. Si hay elementos sueltos, mover y aplanar dentro de target_rf_dir
    for item in loose_items:
        if item.is_file():
            dest = target_rf_dir / item.name
            if not dest.exists():
                shutil.move(str(item), str(dest))
            elif dest.resolve() != item.resolve():
                item.unlink(missing_ok=True)
        elif item.is_dir():
            if item.name.lower() in IGNORED_SUBDIRS:
                shutil.rmtree(item, ignore_errors=True)
                continue

            # Mover recursivamente archivos válidos a target_rf_dir
            for f in list(item.rglob("*")):
                if f.is_file():
                    if any(part.lower() in IGNORED_SUBDIRS for part in f.parts):
                        continue
                    ext = f.suffix.lower()
                    name_low = f.name.lower()
                    if ext in SOURCE_EXTENSIONS or name_low in IMPORTANT_FILENAMES:
                        dest = target_rf_dir / f.name
                        if not dest.exists():
                            shutil.move(str(f), str(dest))
                        elif dest.resolve() != f.resolve():
                            f.unlink(missing_ok=True)

            # Limpiar directorio intermediario si quedó vacío o con basura
            try:
                shutil.rmtree(item, ignore_errors=True)
            except Exception:
                pass

    return target_rf_dir
