"""Cliente para invocar el motor Ripley desde Dredd."""

import json
from pathlib import Path
import shutil
import subprocess
from typing import Any, Dict, List, Optional


from dredd.core.compiler import compile_c_sources
from dredd.core.sandbox import execute_sandboxed, audit_sandbox_evasion


def evaluate_guide_testcases(target_path: Path, guide: Any) -> List[Dict[str, Any]]:
    """Ejecuta los casos de test .in / .out de la guía de Deckard contra los binarios del estudiante en sandbox."""
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

            # Ejecutar casos de prueba en sandbox con límites estrictos de RAM (64MB)
            for tc in ex.test_cases:
                retcode, stdout, stderr, timed_out = execute_sandboxed(
                    cmd=[str(bin_file)],
                    input_data=tc.get("entrada", ""),
                    timeout=5.0,
                    max_memory_mb=64,
                    workspace=target_path,
                )
                expected = tc.get("salida", "").strip()
                actual = stdout.strip()
                passed = (retcode == 0) and (actual == expected or not expected) and not timed_out
                err_msg = stderr.strip() if retcode != 0 else (
                    f"Salida esperada:\n{expected}\nObtenida:\n{actual}" if not passed else ""
                )
                results.append({
                    "name": f"{ex.id} / {tc['nombre']}",
                    "passed": passed,
                    "memory_leak": False,
                    "sanitizer_error": err_msg,
                    "timed_out": timed_out,
                })

    return results


def discover_and_run_local_testcases(target_path: Path) -> List[Dict[str, Any]]:
    """Descubre y ejecuta casos de prueba locales (.in / .out) dentro de la carpeta del estudiante."""
    in_files = sorted(target_path.glob("**/*.in"))
    if not in_files:
        return []

    c_files = sorted([
        f for f in target_path.glob("**/*.c")
        if not any(part.startswith(".") for part in f.parts)
    ])
    if not c_files:
        return []

    import tempfile
    results = []

    with tempfile.TemporaryDirectory() as tmp_d:
        tmp_dir = Path(tmp_d)
        bin_file = tmp_dir / "local_test_bin"
        comp_res = compile_c_sources(c_files, output_bin=bin_file)
        if not comp_res.success:
            return [{
                "name": "compilacion_tests_locales",
                "passed": False,
                "sanitizer_error": comp_res.raw_stderr[:300],
            }]

        for in_f in in_files:
            out_f = in_f.with_suffix(".out")
            expected = out_f.read_text(encoding="utf-8", errors="replace").strip() if out_f.is_file() else ""
            in_data = in_f.read_text(encoding="utf-8", errors="replace")

            retcode, stdout, stderr, timed_out = execute_sandboxed(
                cmd=[str(bin_file)],
                input_data=in_data,
                timeout=5.0,
                max_memory_mb=64,
                workspace=target_path,
            )
            actual = stdout.strip()
            passed = (retcode == 0) and (actual == expected or not expected) and not timed_out
            results.append({
                "name": f"local / {in_f.name}",
                "passed": passed,
                "memory_leak": False,
                "sanitizer_error": stderr.strip() if not passed else "",
                "timed_out": timed_out,
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

    # 4. Auditoría de seguridad y evasión de sandbox en todos los archivos C
    c_files = sorted([
        f for f in target_path.glob("**/*.c")
        if not any(part.startswith(".") for part in f.parts)
    ])
    sec_findings = []
    for c_f in c_files:
        try:
            code_txt = c_f.read_text(encoding="utf-8", errors="replace")
            for sf in audit_sandbox_evasion(code_txt, c_f.name):
                sec_findings.append({
                    "rule_code": sf.rule_code,
                    "rule_name": f"[SEGURIDAD] {sf.title}",
                    "severity": sf.severity,
                    "message": sf.message,
                    "suggestion": "Eliminá llamadas a funciones del sistema o intentos de evasión de sandbox.",
                    "file": c_f.name,
                    "line": sf.line,
                    "code_snippet": sf.code_snippet,
                })
        except Exception:
            pass

    if sec_findings:
        res_dict.setdefault("ast_findings", []).extend(sec_findings)
        res_dict.setdefault("metrics", {})["security_violations"] = len(sec_findings)

    # 5. Ejecutar casos de prueba (de la guía Deckard o descubiertos localmente)
    all_tests = list(res_dict.get("tests", {}).get("cases", []))
    if guide and getattr(guide, "exercises", None):
        guide_tests = evaluate_guide_testcases(target_path, guide)
        if guide_tests:
            all_tests.extend(guide_tests)
    else:
        local_tests = discover_and_run_local_testcases(target_path)
        if local_tests:
            all_tests.extend(local_tests)

    if all_tests:
        res_dict["tests"] = {
            "total": len(all_tests),
            "passed": sum(1 for c in all_tests if c.get("passed")),
            "failed": sum(1 for c in all_tests if not c.get("passed")),
            "cases": all_tests,
        }

    return res_dict

