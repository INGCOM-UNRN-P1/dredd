"""Evaluador para proyectos estructurados en ejercicios con Makefiles (modo conan)."""

from dataclasses import dataclass, field
from pathlib import Path
import subprocess
from typing import Any, Dict, List, Optional, Set


@dataclass
class ExerciseEvalResult:
    exercise_name: str
    clean_ok: bool
    test_ok: bool
    check_ok: bool
    output_log: str = ""


def evaluate_makefile_exercises(
    repo_path: Path,
    timeout_sec: int = 60,
    baseline_dir: Optional[Path] = None,
    uncompleted_exercises: Optional[Set[str]] = None,
) -> List[ExerciseEvalResult]:
    """Busca subdirectorios 'ejercicio*' con Makefile y ejecuta make clean, test y check, ignorando ejercicios sin completar."""
    results = []
    if uncompleted_exercises is None:
        try:
            from dredd.core.baseline import classify_submission_exercises
            b_info = classify_submission_exercises(repo_path, baseline_dir=baseline_dir)
            uncompleted_exercises = set(b_info.get("uncompleted", []))
        except Exception:
            uncompleted_exercises = set()

    candidates = (
        list(repo_path.glob("ejercicio*"))
        + list(repo_path.glob("ejercicios/ejercicio*"))
        + list(repo_path.glob("**/ejercicios/ejercicio*"))
    )
    exercise_dirs = sorted(
        {
            d for d in candidates
            if d.is_dir()
            and (d / "Makefile").is_file()
            and (not uncompleted_exercises or d.name not in uncompleted_exercises)
        },
        key=lambda p: p.name,
    )

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

        # 4. make clean posterior para evitar dejar binarios en el árbol del estudiante
        try:
            subprocess.run(
                ["make", "-C", str(ex_dir), "clean"],
                capture_output=True,
                text=True,
                timeout=timeout_sec,
            )
        except Exception:
            pass

        # Barrido de seguridad: eliminar cualquier binario residual generado durante make
        try:
            from dredd.core.binary_check import is_binary_file
            for p in list(ex_dir.rglob("*")):
                if p.is_file():
                    is_bin, _ = is_binary_file(p.name, p.read_bytes()[:1024])
                    if is_bin:
                        p.unlink(missing_ok=True)
        except Exception:
            pass

        results.append(
            ExerciseEvalResult(
                exercise_name=ex_dir.name,
                clean_ok=clean_ok,
                test_ok=test_ok,
                check_ok=check_ok,
                output_log="\n\n".join(logs),
            )
        )

    # Limpiar modificaciones si es repositorio Git
    if (repo_path / ".git").is_dir():
        subprocess.run(["git", "-C", str(repo_path), "reset", "--hard", "HEAD"], capture_output=True)
        subprocess.run(["git", "-C", str(repo_path), "clean", "-fd"], capture_output=True)

    return results
