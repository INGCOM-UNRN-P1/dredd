"""Cliente para invocar el motor Ripley desde Dredd."""

from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
from typing import Any, Dict, List, Optional, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from dredd.core.config import ToolChecksConfig

from dredd.core.compiler import compile_c_sources
from dredd.core.sandbox import execute_sandboxed, audit_sandbox_evasion
from dredd.core.valgrind import run_valgrind_check, ValgrindReport


def audit_style_with_gaff(
    target_path: Path,
    checks: Optional[ToolChecksConfig] = None,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Ejecuta el linter de estilo Gaff sobre los archivos C y H del estudiante."""
    findings = []
    if target_path.is_file():
        c_and_h_files = [target_path] if target_path.suffix.lower() in (".c", ".h", ".hpp") else []
    else:
        c_and_h_files = sorted([
            f for f in target_path.glob("**/*")
            if f.is_file() and f.suffix.lower() in (".c", ".h", ".hpp") and not any(p.startswith(".") for p in f.parts)
        ])

    enforce_var_len = checks.enforce_variable_length if checks else True

    try:
        from gaff.core.linter import analizar_archivo
        for f in c_and_h_files:
            viols = analizar_archivo(f)
            for v in viols:
                rc = str(v.codigo)
                if not enforce_var_len and rc in ("0x0001h", "GAFF011"):
                    continue
                findings.append({
                    "rule_code": rc,
                    "title": v.titulo,
                    "file": f.name,
                    "line": v.linea,
                    "column": v.columna,
                    "message": v.mensaje,
                    "suggestion": v.sugerencia,
                    "autofixable": getattr(v, "es_autofixable", False),
                })
    except ImportError:
        # Fallback de linter de estilo si gaff no está instalado como paquete Python
        from dredd.core.ast_checker import check_regla_0x0001
        for f in c_and_h_files:
            try:
                content = f.read_text(encoding="utf-8", errors="replace")
                lines = content.splitlines()
                for idx, l in enumerate(lines, start=1):
                    if len(l) > 80:
                        findings.append({
                            "rule_code": "GAFF009",
                            "title": "Línea demasiado larga (> 80 columnas)",
                            "file": f.name,
                            "line": idx,
                            "column": 81,
                            "message": f"La línea tiene {len(l)} caracteres (máximo 80).",
                            "suggestion": "Dividí la sentencia o expresión en múltiples líneas.",
                            "autofixable": False,
                        })
                    if "\t" in l:
                        findings.append({
                            "rule_code": "GAFF010",
                            "title": "Tabulaciones en código fuente",
                            "file": f.name,
                            "line": idx,
                            "column": l.find("\t") + 1,
                            "message": "Uso de tabuladores prohibido. Usar 4 espacios.",
                            "suggestion": "Configurá tu editor para usar 4 espacios en lugar de tabuladores.",
                            "autofixable": True,
                        })
                if enforce_var_len:
                    vars_found = check_regla_0x0001(content)
                    for name, line_num in vars_found:
                        if len(name) == 1 and name.lower() not in ("i", "j", "k", "n", "x", "y", "z", "f", "c", "r"):
                            findings.append({
                                "rule_code": "0x0001h",
                                "title": "Identificador de variable no descriptivo",
                                "file": f.name,
                                "line": line_num,
                                "column": 1,
                                "message": f"Identificador de variable no descriptivo de una sola letra '{name}'.",
                                "suggestion": "Los nombres de variables deben reflejar con precisión su propósito (salvo índices canónicos i, j, k, n, x, y, z, f, c, r).",
                                "autofixable": False,
                            })
                        elif 1 < len(name) < 4 and name.lower() not in ("fd", "fp", "in", "ok"):
                            findings.append({
                                "rule_code": "0x0001h",
                                "title": "Identificador corto y poco expresivo",
                                "file": f.name,
                                "line": line_num,
                                "column": 1,
                                "message": f"Identificador corto y poco expresivo '{name}' ({len(name)} caracteres).",
                                "suggestion": "Se recomienda utilizar identificadores más descriptivos del dominio del problema.",
                                "autofixable": False,
                            })
                        elif len(name) > 31:
                            findings.append({
                                "rule_code": "0x0001h",
                                "title": "Identificador excesivamente largo",
                                "file": f.name,
                                "line": line_num,
                                "column": 1,
                                "message": f"Identificador excesivamente largo '{name}' ({len(name)} caracteres).",
                                "suggestion": "Los identificadores no deben superar los 31 caracteres.",
                                "autofixable": False,
                            })
            except Exception:
                pass

    metrics = {
        "files_analyzed": len(c_and_h_files),
        "total_style_violations": len(findings),
    }
    return findings, metrics


def _run_single_case_in_sandbox(
    bin_file: Path,
    tc_name: str,
    input_data: str,
    expected_output: str,
    workspace: Path,
    timeout: float = 5.0,
    max_memory_mb: int = 64,
) -> Dict[str, Any]:
    """Ejecuta un caso de prueba individual en sandbox y realiza verificación de Valgrind."""
    retcode, stdout, stderr, timed_out = execute_sandboxed(
        cmd=[str(bin_file)],
        input_data=input_data,
        timeout=timeout,
        max_memory_mb=max_memory_mb,
        workspace=workspace,
    )
    expected = expected_output.strip()
    actual = stdout.strip()
    passed = (retcode == 0) and (actual == expected or not expected) and not timed_out

    # Auditoría Valgrind
    val_report = run_valgrind_check(
        cmd=[str(bin_file)],
        input_data=input_data,
        timeout=timeout,
        workspace=workspace,
    )
    memory_leak = val_report.has_leaks or (val_report.total_errors > 0)

    err_msg = stderr.strip() if retcode != 0 else (
        f"Salida esperada:\n{expected}\nObtenida:\n{actual}" if not passed else ""
    )

    diff_str = ""
    if not passed and expected and actual:
        diff_str = f"--- Esperado\n+++ Obtenido\n- {expected}\n+ {actual}"

    return {
        "name": tc_name,
        "passed": passed and not memory_leak,
        "input_data": input_data,
        "expected_output": expected,
        "actual_output": actual,
        "return_code": retcode,
        "timed_out": timed_out,
        "memory_leak": memory_leak,
        "valgrind_report": val_report.to_dict(),
        "sanitizer_error": err_msg,
        "diff": diff_str,
    }


def evaluate_guide_testcases(
    target_path: Path,
    guide: Any,
    tipo_entrega: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Ejecuta los casos de test .in / .out de la guía de Deckard contra los binarios del estudiante en sandbox."""
    if not guide or not getattr(guide, "exercises", None):
        return []

    c_files = sorted([
        f for f in target_path.glob("**/*.c")
        if not any(part.startswith(".") for part in f.parts)
    ])
    if not c_files:
        return []

    from dredd.core.config import (
        MODE_ARCHIVOS_INDIVIDUALES,
        MODE_MAKEFILES_INDIVIDUALES,
        MODE_PROYECTO,
        normalize_delivery_mode,
    )

    mode = normalize_delivery_mode(
        tipo_entrega or getattr(guide, "tipo_entrega", None)
    )
    if mode == MODE_MAKEFILES_INDIVIDUALES:
        return []

    results = []
    import tempfile

    with tempfile.TemporaryDirectory() as tmp_d:
        tmp_dir = Path(tmp_d)

        # 1. Modo Proyecto (con Makefile en la raíz)
        if mode == MODE_PROYECTO and (
            (target_path / "Makefile").is_file()
            or (target_path / "makefile").is_file()
        ):
            from dredd.core.compiler import compile_with_make
            comp_res = compile_with_make(target_path)
            if comp_res.success and comp_res.output_bin:
                bin_file = comp_res.output_bin
                for ex in guide.exercises:
                    if not ex.test_cases:
                        continue
                    for tc in ex.test_cases:
                        case_res = _run_single_case_in_sandbox(
                            bin_file=bin_file,
                            tc_name=f"{ex.id} / {tc['nombre']}",
                            input_data=tc.get("entrada", ""),
                            expected_output=tc.get("salida", ""),
                            workspace=target_path,
                        )
                        results.append(case_res)
                return results

        # 2. Modo Proyecto o Librería multi-archivo (compilar todos los .c juntos)
        if mode in ("proyecto", "libreria"):
            bin_file = tmp_dir / "app_project"
            comp_res = compile_c_sources(c_files, output_bin=bin_file)
            for ex in guide.exercises:
                if not ex.test_cases:
                    continue
                if not comp_res.success:
                    err_summary = comp_res.raw_stderr.strip()[:300]
                    for tc in ex.test_cases:
                        results.append({
                            "name": f"{ex.id} / {tc['nombre']}",
                            "passed": False,
                            "memory_leak": False,
                            "input_data": tc.get("entrada", ""),
                            "expected_output": tc.get("salida", ""),
                            "actual_output": "",
                            "sanitizer_error": f"Error de compilación de proyecto: {err_summary}",
                        })
                    continue

                for tc in ex.test_cases:
                    case_res = _run_single_case_in_sandbox(
                        bin_file=bin_file,
                        tc_name=f"{ex.id} / {tc['nombre']}",
                        input_data=tc.get("entrada", ""),
                        expected_output=tc.get("salida", ""),
                        workspace=target_path,
                    )
                    results.append(case_res)
            return results

        # 3. Modo estándar: archivos individuales
        for ex in guide.exercises:
            if not ex.test_cases:
                continue

            # Buscar archivo relevante para este ejercicio
            matched_files = [f for f in c_files if ex.id.lower() in f.stem.lower() or f.stem.lower() in ex.id.lower()]
            candidate_files = matched_files if matched_files else c_files

            compiled_bin = None
            last_err = ""
            for c_cand in candidate_files:
                bin_file = tmp_dir / f"test_{ex.id}_{c_cand.stem}"
                comp_res = compile_c_sources([c_cand], output_bin=bin_file)
                if comp_res.success and bin_file.is_file():
                    compiled_bin = bin_file
                    break
                else:
                    last_err = comp_res.raw_stderr[:200]

            if not compiled_bin:
                for tc in ex.test_cases:
                    results.append({
                        "name": f"{ex.id} / {tc['nombre']}",
                        "passed": False,
                        "memory_leak": False,
                        "input_data": tc.get("entrada", ""),
                        "expected_output": tc.get("salida", ""),
                        "actual_output": "",
                        "sanitizer_error": f"Error de compilación del ejercicio: {last_err}",
                    })
                continue

            # Ejecutar casos de prueba en sandbox con límites estrictos de RAM (64MB)
            for tc in ex.test_cases:
                case_res = _run_single_case_in_sandbox(
                    bin_file=compiled_bin,
                    tc_name=f"{ex.id} / {tc['nombre']}",
                    input_data=tc.get("entrada", ""),
                    expected_output=tc.get("salida", ""),
                    workspace=target_path,
                )
                results.append(case_res)

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

            case_res = _run_single_case_in_sandbox(
                bin_file=bin_file,
                tc_name=f"local / {in_f.name}",
                input_data=in_data,
                expected_output=expected,
                workspace=target_path,
            )
            results.append(case_res)

    return results


def run_ripley_analysis(
    target_path: Path,
    guide: Optional[Any] = None,
    activity_slug: Optional[str] = None,
    workspace_dir: Optional[Path] = None,
    checks_override: Optional[Any] = None,
    tipo_entrega: Optional[str] = None,
) -> Dict[str, Any]:
    from dredd.core.config import load_dredd_config, ToolChecksConfig

    cfg = load_dredd_config(workspace_dir or target_path)
    if checks_override:
        checks = checks_override
    else:
        checks = cfg.get_effective_checks(activity_slug) if cfg else ToolChecksConfig()

    from dredd.core.config import (
        MODE_ARCHIVOS_INDIVIDUALES,
        MODE_MAKEFILES_INDIVIDUALES,
        MODE_PROYECTO,
        normalize_delivery_mode,
    )

    raw_mode = (
        cfg.get_delivery_mode(
            activity_slug=activity_slug,
            guide_mode=getattr(guide, "tipo_entrega", None),
            target_path=target_path,
            cli_override=tipo_entrega,
        )
        if cfg
        else (
            tipo_entrega
            or getattr(guide, "tipo_entrega", None)
            or "archivos_individuales"
        )
    )
    effective_mode = normalize_delivery_mode(raw_mode)

    def _collect_ast_findings() -> List[Dict[str, Any]]:
        if checks.ripley_enabled:
            try:
                from ripley.core.engine import analyze_target

                res = analyze_target(target_path)
                return res.to_dict().get("ast_findings", [])
            except Exception:
                pass
        from dredd.core.ast_checker import audit_c_file

        findings = []
        for cf in sorted(target_path.glob("**/*.c")):
            if not any(part.startswith(".") for part in cf.parts):
                findings.extend(audit_c_file(cf))
        return findings

    res_dict = None
    c_files = sorted([
        f
        for f in target_path.glob("**/*.c")
        if not any(part.startswith(".") for part in f.parts)
    ])

    if effective_mode == MODE_MAKEFILES_INDIVIDUALES:
        from dredd.core.compiler import compile_with_make
        from dredd.core.makefile_eval import evaluate_makefile_exercises

        makefile_results = evaluate_makefile_exercises(target_path)
        ast_findings = _collect_ast_findings()

        if makefile_results:
            all_passed = all(m.clean_ok and m.test_ok for m in makefile_results)
            res_dict = {
                "version": "2.0.0",
                "compilation": {
                    "success": all_passed,
                    "raw_stderr": "\n".join(
                        m.output_log for m in makefile_results
                    ),
                    "translated_diagnostics": [],
                    "compiler_used": "makefiles_individuales",
                },
                "ast_findings": ast_findings,
                "tests": {
                    "total": len(makefile_results),
                    "passed": sum(1 for m in makefile_results if m.test_ok),
                    "failed": sum(1 for m in makefile_results if not m.test_ok),
                    "cases": [
                        {
                            "name": m.exercise_name,
                            "passed": m.test_ok,
                            "memory_leak": False,
                            "sanitizer_error": (
                                m.output_log if not m.test_ok else ""
                            ),
                        }
                        for m in makefile_results
                    ],
                },
                "metrics": {"c_files_count": len(c_files)},
            }
        elif (target_path / "Makefile").is_file() or (
            target_path / "makefile"
        ).is_file():
            comp_make = compile_with_make(target_path)
            res_dict = {
                "version": "2.0.0",
                "compilation": {
                    "success": comp_make.success,
                    "raw_stderr": comp_make.raw_stderr,
                    "translated_diagnostics": comp_make.translated_diagnostics,
                    "compiler_used": "makefile",
                },
                "ast_findings": ast_findings,
                "tests": {"total": 0, "passed": 0, "failed": 0, "cases": []},
                "metrics": {"c_files_count": len(c_files)},
            }
        else:
            res_dict = {
                "version": "2.0.0",
                "compilation": {
                    "success": False,
                    "raw_stderr": "No se encontraron sub-Makefiles de ejercicios ni Makefile raíz.",
                    "compiler_used": "makefiles_individuales",
                },
                "ast_findings": ast_findings,
                "tests": {"total": 0, "passed": 0, "failed": 0, "cases": []},
                "metrics": {"c_files_count": len(c_files)},
            }

    elif effective_mode == MODE_PROYECTO:
        from dredd.core.compiler import compile_with_make

        comp_make = compile_with_make(target_path)
        ast_findings = _collect_ast_findings()

        test_cases = []
        test_ok = True
        try:
            p_test = subprocess.run(
                ["make", "-C", str(target_path), "test"],
                capture_output=True,
                text=True,
                timeout=60,
            )
            if p_test.returncode == 0:
                test_cases.append({
                    "name": "make_test",
                    "passed": True,
                    "memory_leak": False,
                    "sanitizer_error": "",
                })
            else:
                test_ok = False
                test_cases.append({
                    "name": "make_test",
                    "passed": False,
                    "memory_leak": False,
                    "sanitizer_error": (
                        p_test.stderr or p_test.stdout
                    ).strip()[:300],
                })
        except Exception:
            pass

        res_dict = {
            "version": "2.0.0",
            "compilation": {
                "success": comp_make.success and test_ok,
                "raw_stderr": comp_make.raw_stderr,
                "translated_diagnostics": comp_make.translated_diagnostics,
                "compiler_used": "make_proyecto",
            },
            "ast_findings": ast_findings,
            "tests": {
                "total": len(test_cases),
                "passed": sum(1 for c in test_cases if c.get("passed")),
                "failed": sum(1 for c in test_cases if not c.get("passed")),
                "cases": test_cases,
            },
            "metrics": {"c_files_count": len(c_files)},
        }

    else:
        # Modo 'archivos_individuales'
        # 1. Intentar importación directa de Ripley si está disponible en el entorno
        if checks.ripley_enabled:
            try:
                from ripley.core.engine import analyze_target

                result = analyze_target(target_path)
                res_dict = result.to_dict()
            except Exception:
                pass

        # 2. Intentar ejecución vía comando CLI de ripley si no se obtuvo por import
        if res_dict is None and checks.ripley_enabled:
            ripley_bin = shutil.which("ripley") or shutil.which("ripley-check")
            if ripley_bin:
                try:
                    proc = subprocess.run(
                        [
                            ripley_bin,
                            "analyze",
                            str(target_path),
                            "--format",
                            "json",
                        ],
                        capture_output=True,
                        text=True,
                        timeout=30,
                    )
                    if proc.stdout.strip():
                        res_dict = json.loads(proc.stdout)
                except Exception:
                    pass

        # 3. Fallback nativo: compilación por archivo C individual + análisis AST nativo
        if res_dict is None:
            from dredd.core.ast_checker import audit_c_file

            ast_findings = []
            for c_file in c_files:
                ast_findings.extend(audit_c_file(c_file))

            if not c_files:
                res_dict = {
                    "version": "2.0.0",
                    "compilation": {
                        "success": False,
                        "raw_stderr": "No se encontraron archivos .c",
                        "compiler_used": "none",
                    },
                    "ast_findings": [],
                    "tests": {
                        "total": 0,
                        "passed": 0,
                        "failed": 0,
                        "cases": [],
                    },
                    "metrics": {},
                }
            else:
                file_compilations = {}
                all_diags = []
                all_stderrs = []
                files_comp_ok = True

                import tempfile

                with tempfile.TemporaryDirectory() as tmp_d:
                    tmp_dir = Path(tmp_d)
                    for idx, c_f in enumerate(c_files):
                        tmp_bin = tmp_dir / f"bin_eval_{idx}"
                        comp_f = compile_c_sources([c_f], output_bin=tmp_bin)
                        file_compilations[c_f.name] = {
                            "success": comp_f.success,
                            "raw_stderr": comp_f.raw_stderr,
                            "translated_diagnostics": (
                                comp_f.translated_diagnostics
                            ),
                            "compiler_used": comp_f.compiler_used,
                        }
                        if not comp_f.success:
                            files_comp_ok = False
                            all_stderrs.append(
                                f"[{c_f.name}]:\n{comp_f.raw_stderr}"
                            )
                        all_diags.extend(comp_f.translated_diagnostics)

                res_dict = {
                    "version": "2.0.0",
                    "compilation": {
                        "success": files_comp_ok,
                        "raw_stderr": "\n\n".join(all_stderrs),
                        "translated_diagnostics": all_diags,
                        "compiler_used": checks.daedalus_compiler,
                        "files": file_compilations,
                    },
                    "ast_findings": ast_findings,
                    "tests": {
                        "total": 0,
                        "passed": 0,
                        "failed": 0,
                        "cases": [],
                    },
                    "metrics": {"c_files_count": len(c_files)},
                }

    # 4. Auditoría de seguridad y evasión de sandbox (Kaneda)
    if checks.kaneda_enabled:
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

    # 5. Filtrar hallazgos de Ripley según reglas activas/deshabilitadas
    if "ast_findings" in res_dict:
        raw_findings = res_dict["ast_findings"]
        filtered = []
        is_all_rules = any(en.lower() in ("all", "*") for en in checks.ripley_rules) if checks.ripley_rules else True
        for f in raw_findings:
            rc = (f.get("rule_code") or f.get("rule_id") or "").lower()
            # Si la regla está deshabilitada explícitamente, ignorarla
            if any(rc == dis.lower() for dis in checks.ripley_disabled_rules):
                continue
            # Si hay lista blanca de reglas de Ripley y no es un hallazgo de seguridad
            if checks.ripley_rules and not is_all_rules and not rc.startswith("sec") and not f.get("rule_name", "").startswith("[SEGURIDAD]"):
                if not any(rc == en.lower() for en in checks.ripley_rules):
                    continue
            filtered.append(f)
        res_dict["ast_findings"] = filtered

    # 6. Ejecutar casos de prueba bajo sandbox configurado
    all_tests = list(res_dict.get("tests", {}).get("cases", []))
    if guide and getattr(guide, "exercises", None):
        guide_tests = evaluate_guide_testcases(
            target_path, guide, tipo_entrega=effective_mode
        )
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

    # 7. Consolidar reporte de Valgrind / Memoria
    val_executed = False
    val_clean = True
    def_lost = 0
    ind_lost = 0
    pos_lost = 0
    reach_lost = 0
    tot_errs = 0
    val_errors = []

    for tc in all_tests:
        v_rep = tc.get("valgrind_report")
        if v_rep and v_rep.get("executed"):
            val_executed = True
            if not v_rep.get("clean"):
                val_clean = False
            def_lost += v_rep.get("definitely_lost_bytes", 0)
            ind_lost += v_rep.get("indirectly_lost_bytes", 0)
            pos_lost += v_rep.get("possibly_lost_bytes", 0)
            reach_lost += v_rep.get("still_reachable_bytes", 0)
            tot_errs += v_rep.get("total_errors", 0)
            val_errors.extend(v_rep.get("errors", []))

    res_dict["valgrind"] = {
        "executed": val_executed,
        "clean": val_clean and (def_lost == 0) and (ind_lost == 0) and (pos_lost == 0) and (tot_errs == 0),
        "definitely_lost_bytes": def_lost,
        "indirectly_lost_bytes": ind_lost,
        "possibly_lost_bytes": pos_lost,
        "still_reachable_bytes": reach_lost,
        "total_errors": tot_errs,
        "errors": val_errors,
    }

    # 8. Auditoría de estilo y convenciones arquitectónicas (Gaff)
    if checks.gaff_enabled:
        style_findings, style_metrics = audit_style_with_gaff(target_path, checks=checks)
        res_dict["style_findings"] = style_findings
        res_dict["style_metrics"] = style_metrics

    return res_dict

