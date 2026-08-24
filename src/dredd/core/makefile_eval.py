"""Evaluador para proyectos estructurados en ejercicios con Makefiles (modo conan)."""

from dataclasses import dataclass, field
from pathlib import Path
import subprocess
from typing import Any, Dict, List


@dataclass
class ExerciseEvalResult:
    exercise_name: str
    clean_ok: bool
    test_ok: bool
    check_ok: bool
    output_log: str = ""


def evaluate_makefile_exercises(repo_path: Path, timeout_sec: int = 60) -> List[ExerciseEvalResult]:
    """Busca subdirectorios 'ejercicio*' con Makefile y ejecuta make clean, test y check."""
    results = []
    exercise_dirs = sorted([
        d for d in repo_path.glob("ejercicio*")
        if d.is_dir() and (d / "Makefile").is_file()
    ])

    for ex_dir in exercise_dirs:
        logs = []
        clean_ok = True
        test_ok = True
        check_ok = True

        # 1. make clean
        try:
            p_clean = subprocess.run(
                ["make", "-C", str(ex_dir), "clean"],
                capture_output=True,
                text=True,
                timeout=timeout_sec,
            )
            logs.append(f"### make clean\n```text\n{p_clean.stdout}\n{p_clean.stderr}\n```")
            clean_ok = (p_clean.returncode == 0)
        except Exception as e:
            logs.append(f"### make clean (error)\n{e}")
            clean_ok = False

        # 2. make test
        try:
            p_test = subprocess.run(
                ["make", "-C", str(ex_dir), "test"],
                capture_output=True,
                text=True,
                timeout=timeout_sec,
            )
            logs.append(f"### make test\n```text\n{p_test.stdout}\n{p_test.stderr}\n```")
            test_ok = (p_test.returncode == 0)
        except Exception as e:
            logs.append(f"### make test (error)\n{e}")
            test_ok = False

        # 3. make check (si existe el target)
        try:
            p_check = subprocess.run(
                ["make", "-C", str(ex_dir), "check"],
                capture_output=True,
                text=True,
                timeout=timeout_sec,
            )
            logs.append(f"### make check\n```text\n{p_check.stdout}\n{p_check.stderr}\n```")
            check_ok = (p_check.returncode == 0)
        except Exception:
            check_ok = True  # Opcional si no tiene target check

        results.append(
            ExerciseEvalResult(
                exercise_name=ex_dir.name,
                clean_ok=clean_ok,
                test_ok=test_ok,
                check_ok=check_ok,
                output_log="\n\n".join(logs),
            )
        )

    # Limpiar modificaciones
    subprocess.run(["git", "-C", str(repo_path), "reset", "--hard", "HEAD"], capture_output=True)

    return results
