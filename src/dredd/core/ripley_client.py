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

    # 3. Fallback de emergencia: compilación básica con GCC
    c_files = sorted(target_path.glob("**/*.c"))
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
            "ast_findings": [],
            "tests": {"total": 0, "passed": 0, "failed": 0, "cases": []},
            "metrics": {"c_files_count": len(c_files)},
        }

    return {
        "version": "2.0.0",
        "compilation": {"success": False, "raw_stderr": "Ni Ripley ni GCC se encuentran disponibles."},
        "ast_findings": [],
        "tests": {"total": 0, "passed": 0, "failed": 0, "cases": []},
        "metrics": {},
    }
