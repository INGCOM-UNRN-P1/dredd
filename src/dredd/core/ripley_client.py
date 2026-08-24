"""Cliente para invocar el motor Ripley desde Dredd."""

import json
from pathlib import Path
import shutil
import subprocess
from typing import Any, Dict


def run_ripley_analysis(target_path: Path) -> Dict[str, Any]:
    """Ejecuta el análisis técnico sobre la entrega del estudiante usando Ripley."""
    # 1. Intentar importación directa si Ripley está en el entorno Python
    try:
        from ripley.core.engine import analyze_target
        result = analyze_target(target_path)
        return result.to_dict()
    except ImportError:
        pass

    # 2. Intentar ejecución vía comando CLI de ripley
    ripley_bin = shutil.which("ripley") or shutil.which("ripley-check")
    if ripley_bin:
        try:
            proc = subprocess.run(
                [ripley_bin, "analyze", str(target_path), "--format", "json"],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if proc.stdout.strip():
                return json.loads(proc.stdout)
        except Exception:
            pass

    # 3. Fallback nativo: compilación con GCC + análisis AST nativo de Dredd
    from dredd.core.ast_checker import audit_c_file
    from dredd.core.makefile_eval import evaluate_makefile_exercises

    c_files = sorted([
        f for f in target_path.glob("**/*.c")
        if not any(part.startswith(".") for part in f.parts)
    ])

    ast_findings = []
    for c_file in c_files:
        ast_findings.extend(audit_c_file(c_file))

    # Soporte para proyectos modulares de ejercicios (conan mode)
    makefile_results = evaluate_makefile_exercises(target_path)
    if makefile_results:
        all_passed = all(m.clean_ok and m.test_ok for m in makefile_results)
        return {
            "version": "2.0.0",
            "compilation": {
                "success": all_passed,
                "raw_stderr": "\n".join(m.output_log for m in makefile_results),
                "translated_diagnostics": [],
            },
            "ast_findings": ast_findings,
            "tests": {
                "total": len(makefile_results),
                "passed": sum(1 for m in makefile_results if m.test_ok),
                "failed": sum(1 for m in makefile_results if not m.test_ok),
                "cases": [
                    {"name": m.exercise_name, "passed": m.test_ok, "memory_leak": False, "sanitizer_error": m.output_log if not m.test_ok else ""}
                    for m in makefile_results
                ],
            },
            "metrics": {"c_files_count": len(c_files)},
        }

    if not c_files:
        return {
            "version": "2.0.0",
            "compilation": {"success": False, "raw_stderr": "No se encontraron archivos .c"},
            "ast_findings": [],
            "tests": {"total": 0, "passed": 0, "failed": 0, "cases": []},
            "metrics": {},
        }

    gcc = shutil.which("gcc")
    if gcc:
        cmd = [gcc, "-Wall", "-Wextra", "-std=c11"] + [str(f) for f in c_files] + ["-o", "/dev/null"]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        return {
            "version": "2.0.0",
            "compilation": {
                "success": proc.returncode == 0,
                "raw_stderr": proc.stderr,
                "translated_diagnostics": [],
            },
            "ast_findings": ast_findings,
            "tests": {"total": 0, "passed": 0, "failed": 0, "cases": []},
            "metrics": {"c_files_count": len(c_files)},
        }

    return {
        "version": "2.0.0",
        "compilation": {"success": False, "raw_stderr": "Ni Ripley ni GCC se encuentran disponibles."},
        "ast_findings": ast_findings,
        "tests": {"total": 0, "passed": 0, "failed": 0, "cases": []},
        "metrics": {},
    }

