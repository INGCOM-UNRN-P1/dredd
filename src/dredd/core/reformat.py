"""Reformateador de directorios de entrega para preservar fuentes originales en rN y generar rN_f para revisión manual."""

from __future__ import annotations

from pathlib import Path
import re
import shutil
import subprocess
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


ALLMAN_CLANG_STYLE = (
    "{BasedOnStyle: LLVM, BreakBeforeBraces: Allman, "
    "AllowShortIfStatementsOnASingleLine: false, AllowShortBlocksOnASingleLine: false, "
    "AllowShortLoopsOnASingleLine: false, AllowShortFunctionsOnASingleLine: None, "
    "IndentWidth: 4, TabWidth: 4, UseTab: Never, IndentCaseLabels: true, "
    "ColumnLimit: 80, SpaceBeforeParens: ControlStatements, PointerAlignment: Right}"
)


def format_c_sources_in_place(target_dir: Path) -> None:
    """Aplica autoformato con estilo Allman (clang-format) a archivos C/H dentro de target_dir para revisión manual docente."""
    if not target_dir.is_dir():
        return

    c_files = [f for f in target_dir.iterdir() if f.is_file() and f.suffix.lower() in (".c", ".h")]
    if not c_files:
        return

    try:
        subprocess.run(
            ["clang-format", "-i", f"-style={ALLMAN_CLANG_STYLE}", *[str(f) for f in c_files]],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=10,
        )
    except Exception:
        pass


def generate_rn_f_copy(r_dir: Path, rf_dir: Path) -> None:
    """Genera o actualiza la copia rN_f a partir de rN aplicando autoformato para lectura manual."""
    rf_dir.mkdir(parents=True, exist_ok=True)
    for src in r_dir.iterdir():
        if src.is_file():
            dest = rf_dir / src.name
            shutil.copy2(src, dest)
    format_c_sources_in_place(rf_dir)


def reformat_submission_to_rn_f(
    student_dir: Path,
    target_version: Optional[int] = None,
) -> Path:
    """Estructura el directorio de entrega del estudiante preservando la entrega original 'como llegó' en rN
    y generando en paralelo rN_f para revisión manual docente.

    1. Preserva rN intacto con el código original entregado por el estudiante.
    2. Si hay archivos sueltos o subcarpetas, los ubica de forma aplanada en rN sin alterar su contenido.
    3. Genera rN_f como copia formateada (clang-format) para facilitar la lectura del docente.
    4. Devuelve la ruta a rN (la entrega original) para que TODAS las acciones automatizadas se ejecuten en ella.
    """
    student_dir = Path(student_dir).resolve()
    if not student_dir.is_dir():
        return student_dir

    existing_r = find_existing_revision_folders(student_dir)

    # 1. Recolectar archivos sueltos fuera de cualquier carpeta r* o r*_f o .git / .md / .db
    loose_items: List[Path] = []
    for item in student_dir.iterdir():
        if item.name.startswith(".") or item.name.endswith(".md") or item.name == ".metadata.db":
            continue
        # Omitir carpetas de revisión rN, rN_f, rNi o rN_i
        if item.is_dir() and re.match(r"^r\d+(?:_f|_i|i)?$", item.name, re.IGNORECASE):
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
    target_rf_dir = student_dir / f"r{version_num}f"
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

    # 4. Generar la copia formateada rNf para revisión manual docente
    generate_rn_f_copy(target_r_dir, target_rf_dir)

    # 5. Asegurar que cualquier otra revisión rN existente también tenga su rNf sincronizado
    for num, r_folder in existing_r:
        rf_folder = student_dir / f"r{num}f"
        if not rf_folder.exists():
            generate_rn_f_copy(r_folder, rf_folder)

    # Devolver la entrega original rN para que todas las evaluaciones se ejecuten sobre ella
    return target_r_dir
