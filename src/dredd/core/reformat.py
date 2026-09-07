"""Reformateador de directorios de entrega para preservar fuentes originales en rN sin generar carpetas rNf."""

from __future__ import annotations

from pathlib import Path
import re
import shutil
from typing import List, Optional, Set


SOURCE_EXTENSIONS = {".c", ".h", ".in", ".out", ".txt", ".dat", ".csv"}
IMPORTANT_FILENAMES = {"makefile", "cmakelists.txt", "casos.yaml", "tests.json"}
IGNORED_SUBDIRS = {"__macosx", ".git", ".idea", ".vscode", "__pycache__"}


def find_existing_revision_folders(student_dir: Path) -> List[tuple[int, Path]]:
    """Encuentra carpetas de revisión originales (r1, r2, etc.) ordenadas por número."""
    if not student_dir.is_dir():
        return []

    revs: List[tuple[int, Path]] = []
    for item in student_dir.iterdir():
        if not item.is_dir():
            continue
        m = re.match(r"^r(\d+)$", item.name, re.IGNORECASE)
        if m:
            revs.append((int(m.group(1)), item))

    return sorted(revs, key=lambda x: x[0])


def reformat_submission_to_rn(
    student_dir: Path,
    target_version: Optional[int] = None,
) -> Path:
    """Estructura el directorio de entrega del estudiante preservando la entrega original 'como llegó' en rN.

    1. Preserva rN intacto con el código original entregado por el estudiante.
    2. Si hay archivos sueltos o subcarpetas, los ubica de forma aplanada en rN sin alterar su contenido.
    3. Asegura el directorio rNi para los reportes individuales de las herramientas.
    4. Elimina cualquier carpeta rNf o rN_f residual que genere confusión.
    """
    student_dir = Path(student_dir).resolve()
    if not student_dir.is_dir():
        return student_dir

    # Eliminar carpetas residuales r*f o r*_f si existieran
    for rf in list(student_dir.iterdir()):
        if rf.is_dir() and re.match(r"^r\d+(?:_f|f)$", rf.name, re.IGNORECASE):
            shutil.rmtree(rf, ignore_errors=True)

    existing_r = find_existing_revision_folders(student_dir)

    # 1. Recolectar archivos sueltos fuera de cualquier carpeta r* o .git / .md / .db
    loose_items: List[Path] = []
    for item in student_dir.iterdir():
        if item.name.startswith(".") or item.name.endswith((".md", ".log")) or item.name == ".metadata.db":
            continue
        # Omitir carpetas de revisión rN, rNi o rN_i
        if item.is_dir() and re.match(r"^r\d+(?:_i|i)?$", item.name, re.IGNORECASE):
            continue
        loose_items.append(item)

    # 2. Determinar el número de revisión N
    if target_version is not None:
        version_num = target_version
    elif existing_r and not loose_items:
        # Ya está estructurado, usar la última revisión existente
        version_num = existing_r[-1][0]
    elif existing_r and loose_items:
        # Nueva entrega sobre una existente -> r{max + 1}
        version_num = existing_r[-1][0] + 1
    else:
        # Primera entrega
        version_num = 1

    target_r_dir = student_dir / f"r{version_num}"
    target_rni_dir = student_dir / f"r{version_num}i"
    target_r_dir.mkdir(parents=True, exist_ok=True)
    target_rni_dir.mkdir(parents=True, exist_ok=True)

    # 3. Si hay elementos sueltos, mover y aplanar dentro de target_r_dir (original como llegó)
    for item in loose_items:
        if item.is_file():
            dest = target_r_dir / item.name
            if not dest.exists():
                shutil.move(str(item), str(dest))
            elif dest.resolve() != item.resolve():
                item.unlink(missing_ok=True)
        elif item.is_dir():
            if item.name.lower() in IGNORED_SUBDIRS:
                shutil.rmtree(item, ignore_errors=True)
                continue

            for f in list(item.rglob("*")):
                if f.is_file():
                    if any(part.lower() in IGNORED_SUBDIRS for part in f.parts):
                        continue
                    ext = f.suffix.lower()
                    name_low = f.name.lower()
                    if ext in SOURCE_EXTENSIONS or name_low in IMPORTANT_FILENAMES:
                        dest = target_r_dir / f.name
                        if not dest.exists():
                            shutil.move(str(f), str(dest))
                        elif dest.resolve() != f.resolve():
                            f.unlink(missing_ok=True)

            try:
                shutil.rmtree(item, ignore_errors=True)
            except Exception:
                pass

    return target_r_dir


# Alias retrocompatible
reformat_submission_to_rn_f = reformat_submission_to_rn
