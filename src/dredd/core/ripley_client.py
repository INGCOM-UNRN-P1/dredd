"""Cliente para invocar el motor Ripley desde Dredd."""

import json
from pathlib import Path
import shutil
import subprocess
from typing import Any, Dict, List, Optional


from dredd.core.compiler import compile_c_sources


def evaluate_guide_testcases(target_path: Path, guide: Any) -> List[Dict[str, Any]]:
    """Ejecuta los casos de test .in / .out de la guía de Deckard contra los binarios del estudiante."""
    if not guide or not getattr(guide, "exercises", None):
        return []

    c_files = sorted([
        f for f in target_path.glob("**/*.c")
        if not any(part.startswith(".") for part in f.parts)
    ])
    if not c_files:
        return []

    results = []
    import tempfile

    with tempfile.TemporaryDirectory() as tmp_d:
        tmp_dir = Path(tmp_d)

        for ex in guide.exercises:
            if not ex.test_cases:
                continue

            # Buscar archivos relevantes para este ejercicio
            relevant_files = [f for f in c_files if ex.id.lower() in f.stem.lower() or f.stem.lower() in ex.id.lower()]
            if not relevant_files:
                relevant_files = c_files

            bin_file = tmp_dir / f"test_{ex.id}"
            comp_res = compile_c_sources(relevant_files, output_bin=bin_file)
            if not comp_res.success:
                err_summary = comp_res.raw_stderr.strip()[:300]
                if comp_res.translated_diagnostics:
                    d = comp_res.translated_diagnostics[0]
                    err_summary = f"{d.get('translated_message', '')} ({d.get('suggestion', '')})"
                for tc in ex.test_cases:
                    results.append({
                        "name": f"{ex.id} / {tc['nombre']}",
                        "passed": False,
                        "memory_leak": False,
                        "sanitizer_error": f"Error de compilación: {err_summary}",
                    })
                continue

            # Ejecutar casos de prueba
            for tc in ex.test_cases:
                try:
                    p_run = subprocess.run(
                        [str(bin_file)],
                        input=tc.get("entrada", ""),
                        capture_output=True,
                        text=True,
                        timeout=5,
                    )
                    expected = tc.get("salida", "").strip()
                    actual = p_run.stdout.strip()
                    passed = (p_run.returncode == 0) and (actual == expected or not expected)
                    err_msg = p_run.stderr.strip() if p_run.returncode != 0 else (
                        f"Salida esperada:\n{expected}\nObtenida:\n{actual}" if not passed else ""
                    )
                    results.append({
                        "name": f"{ex.id} / {tc['nombre']}",
                        "passed": passed,
                        "memory_leak": False,
                        "sanitizer_error": err_msg,
                    })
                except subprocess.TimeoutExpired:
                    results.append({
                        "name": f"{ex.id} / {tc['nombre']}",
                        "passed": False,
                        "memory_leak": False,
                        "sanitizer_error": "Timeout (tiempo de ejecución excedido)",
                        "timed_out": True,
                    })
                except Exception as e:
                    results.append({
                        "name": f"{ex.id} / {tc['nombre']}",
                        "passed": False,
                        "memory_leak": False,
                        "sanitizer_error": str(e),
                    })

    return results


def run_ripley_analysis(target_path: Path, guide: Optional[Any] = None) -> Dict[str, Any]:
    """Ejecuta el análisis técnico sobre la entrega del estudiante usando Ripley y la guía de Deckard."""
    # 1. Intentar importación directa si Ripley está en el entorno Python
    res_dict = None
    try:
        from ripley.core.engine import analyze_target
        result = analyze_target(target_path)
        res_dict = result.to_dict()
    except ImportError:
        pass

    # 2. Intentar ejecución vía comando CLI de ripley si no se obtuvo por import
    if res_dict is None:
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
                    res_dict = json.loads(proc.stdout)
            except Exception:
                pass

    # 3. Fallback nativo: compilación con ESPER / GCC + análisis AST nativo de Dredd
    if res_dict is None:
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
            res_dict = {
                "version": "2.0.0",
                "compilation": {
                    "success": all_passed,
                    "raw_stderr": "\n".join(m.output_log for m in makefile_results),
                    "translated_diagnostics": [],
                    "compiler_used": "makefile",
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
        elif not c_files:
            res_dict = {
                "version": "2.0.0",
                "compilation": {"success": False, "raw_stderr": "No se encontraron archivos .c", "compiler_used": "none"},
                "ast_findings": [],
                "tests": {"total": 0, "passed": 0, "failed": 0, "cases": []},
                "metrics": {},
            }
        else:
            comp_res = compile_c_sources(c_files, output_bin=None)
            res_dict = {
                "version": "2.0.0",
                "compilation": {
                    "success": comp_res.success,
                    "raw_stderr": comp_res.raw_stderr,
                    "translated_diagnostics": comp_res.translated_diagnostics,
                    "compiler_used": comp_res.compiler_used,
                },
                "ast_findings": ast_findings,
                "tests": {"total": 0, "passed": 0, "failed": 0, "cases": []},
                "metrics": {"c_files_count": len(c_files)},
            }

    # 4. Si la guía de Deckard provee casos de prueba, integrarlos a los resultados
    if guide and getattr(guide, "exercises", None):
        guide_tests = evaluate_guide_testcases(target_path, guide)
        if guide_tests:
            existing_tests = res_dict.get("tests", {}).get("cases", [])
            all_cases = existing_tests + guide_tests
            res_dict["tests"] = {
                "total": len(all_cases),
                "passed": sum(1 for c in all_cases if c.get("passed")),
                "failed": sum(1 for c in all_cases if not c.get("passed")),
                "cases": all_cases,
            }

    return res_dict

