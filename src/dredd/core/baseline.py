"""Módulo para detección, comparación y filtrado contra la plantilla de entrega (_baseline)."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Set, Tuple


BOILERPLATE_SOURCE_NAMES = {"main.c", "prueba.c", "main.cpp", "test.c", "tests.c"}


def strip_c_comments(text: str) -> str:
    """Elimina comentarios de bloque y de línea en C para comparar únicamente código sustantivo."""
    t = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
    t = re.sub(r"//.*$", "", t, flags=re.MULTILINE)
    return t.strip()


def is_file_unmodified_from_baseline(student_file: Path, baseline_file: Path) -> bool:
    """Determina si un archivo fuente del estudiante permanece idéntico o sin implementar respecto a la plantilla."""
    if not student_file.is_file() or not baseline_file.is_file():
        return False
    try:
        s_bytes = student_file.read_bytes()
        b_bytes = baseline_file.read_bytes()
        if s_bytes == b_bytes:
            return True

        s_text = student_file.read_text(encoding="utf-8", errors="replace")
        b_text = baseline_file.read_text(encoding="utf-8", errors="replace")
        if s_text.strip() == b_text.strip():
            return True

        # Si el archivo del estudiante quedó completamente vacío
        if not s_text.strip():
            return True

        # Si tras quitar comentarios ambos archivos no contienen código o tienen el mismo código base
        s_clean = strip_c_comments(s_text)
        b_clean = strip_c_comments(b_text)
        if s_clean == b_clean or (not s_clean and not b_clean):
            return True
    except Exception:
        pass
    return False


def find_baseline_dir(
    target_path: Path,
    submissions_dir: Optional[Path] = None,
    workspace_dir: Optional[Path] = None,
    explicit_baseline: Optional[Path] = None,
) -> Optional[Path]:
    """Busca el directorio _baseline según la jerarquía de precedencia."""
    if explicit_baseline:
        exp = Path(explicit_baseline).resolve()
        if exp.is_dir():
            return exp

    if submissions_dir:
        cand = Path(submissions_dir) / "_baseline"
        if cand.is_dir():
            return cand

    curr = Path(target_path).resolve()
    for _ in range(5):
        cand = curr / "_baseline"
        if cand.is_dir() and cand != curr:
            return cand
        if curr.parent == curr:
            break
        curr = curr.parent

    if workspace_dir:
        cand_ws = Path(workspace_dir) / "_baseline"
        if cand_ws.is_dir():
            return cand_ws

    return None


def resolve_baseline_revision(baseline_root: Path, revision_str: Optional[str] = None) -> Path:
    """Resuelve la subcarpeta de revisión r1/r2 dentro de _baseline si existe, o el directorio base."""
    if revision_str:
        rev_cand = baseline_root / revision_str
        if rev_cand.is_dir():
            return rev_cand
    if (baseline_root / "r1").is_dir():
        return baseline_root / "r1"
    return baseline_root


def get_exercise_sources(exercise_dir: Path) -> List[Path]:
    """Obtiene los archivos fuente sustantivos del ejercicio."""
    all_c_h = sorted(list(exercise_dir.glob("*.[ch]")) + list(exercise_dir.glob("*.cpp")) + list(exercise_dir.glob("*.hpp")))
    substantive = [f for f in all_c_h if f.name not in BOILERPLATE_SOURCE_NAMES]
    return substantive if substantive else all_c_h


def is_exercise_dir_completed(
    exercise_dir: Path,
    baseline_revision_dir: Path,
) -> Tuple[bool, str]:
    """Verifica si un subdirectorio de ejercicio ha sido completado/modificado respecto a _baseline."""
    sources = get_exercise_sources(exercise_dir)
    if not sources:
        return False, "Sin archivos fuente implementados"

    # Si existe una subcarpeta homónima en baseline (ej. _baseline/r1/ejercicio1)
    base_sub = baseline_revision_dir / exercise_dir.name
    if base_sub.is_dir():
        base_files = {f.name: f for f in base_sub.rglob("*") if f.is_file()}
    else:
        base_files = {f.name: f for f in baseline_revision_dir.rglob("*") if f.is_file()}

    unmodified_count = 0
    modified_count = 0

    for sf in sources:
        bf = base_files.get(sf.name)
        if bf:
            if is_file_unmodified_from_baseline(sf, bf):
                unmodified_count += 1
            else:
                modified_count += 1
        else:
            if sf.stat().st_size > 0:
                modified_count += 1

    if modified_count > 0:
        return True, f"Modificado ({modified_count} archivo(s) alterados respecto a _baseline)"

    return False, f"Sin modificaciones respecto a _baseline ({unmodified_count} archivo(s) idénticos a plantilla)"


def classify_submission_exercises(
    submission_path: Path,
    baseline_dir: Optional[Path] = None,
    revision_str: Optional[str] = None,
) -> Dict[str, Any]:
    """Clasifica los ejercicios de la entrega en completados e incompletos/ignorados.

    Soporta estructura modular en subdirectorios (ejercicios/ejercicioN) y archivos planos (ejercicioN.c).
    """
    if not baseline_dir:
        baseline_dir = find_baseline_dir(submission_path)

    if not baseline_dir:
        return {
            "has_baseline": False,
            "baseline_dir": None,
            "completed": [],
            "uncompleted": [],
            "status_by_exercise": {},
        }

    base_rev_dir = resolve_baseline_revision(baseline_dir, revision_str)

    # 1. Chequear si hay subdirectorios de ejercicios
    raw_dirs = (
        list(submission_path.glob("ejercicio*"))
        + list(submission_path.glob("ejercicios/ejercicio*"))
        + list(submission_path.glob("**/ejercicios/ejercicio*"))
    )
    exercise_dirs = sorted(
        {d for d in raw_dirs if d.is_dir() and re.match(r"^ejercicio\d+$", d.name, re.IGNORECASE)},
        key=lambda p: p.name,
    )

    completed = []
    uncompleted = []
    status_map = {}

    if exercise_dirs:
        for ed in exercise_dirs:
            is_done, reason = is_exercise_dir_completed(ed, base_rev_dir)
            status_map[ed.name] = {
                "completed": is_done,
                "reason": reason,
                "path": str(ed),
            }
            if is_done:
                completed.append(ed.name)
            else:
                uncompleted.append(ed.name)
    else:
        # 2. Chequear archivos planos ejercicioN.c
        flat_c_files = sorted(
            [f for f in submission_path.glob("**/*.[ch]") if re.match(r"^ejercicio\d+$", f.stem, re.IGNORECASE)],
            key=lambda p: p.name,
        )
        base_files = {f.name: f for f in base_rev_dir.rglob("*") if f.is_file()}

        by_stem: Dict[str, List[Path]] = {}
        for f in flat_c_files:
            by_stem.setdefault(f.stem, []).append(f)

        for stem, files in sorted(by_stem.items()):
            is_done = False
            for sf in files:
                bf = base_files.get(sf.name)
                if bf:
                    if not is_file_unmodified_from_baseline(sf, bf):
                        is_done = True
                        break
                elif sf.stat().st_size > 0:
                    is_done = True
                    break

            reason = "Modificado respecto a _baseline" if is_done else "Idéntico a plantilla _baseline"
            status_map[stem] = {
                "completed": is_done,
                "reason": reason,
                "path": str(files[0].parent),
            }
            if is_done:
                completed.append(stem)
            else:
                uncompleted.append(stem)

    return {
        "has_baseline": True,
        "baseline_dir": base_rev_dir,
        "completed": completed,
        "uncompleted": uncompleted,
        "status_by_exercise": status_map,
    }
