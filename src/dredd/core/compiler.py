"""Módulo de compilación C para Dredd usando ESPER con fallback a GCC."""

from dataclasses import dataclass, field
import json
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Any, Dict, List, Optional


@dataclass
class CompilationResult:
    success: bool
    output_bin: Optional[Path] = None
    raw_stderr: str = ""
    translated_diagnostics: List[Dict[str, Any]] = field(default_factory=list)
    compiler_used: str = "gcc"


def _try_import_esper():
    try:
        from esper.core.gcc_parser import run_gcc_and_explain
        return run_gcc_and_explain
    except ImportError:
        # Intentar ubicar esper en el workspace de herramientas
        sibling_esper = Path(__file__).resolve().parents[3] / "esper" / "src"
        if sibling_esper.is_dir() and str(sibling_esper) not in sys.path:
            sys.path.insert(0, str(sibling_esper))
            try:
                from esper.core.gcc_parser import run_gcc_and_explain
                return run_gcc_and_explain
            except ImportError:
                return None
        return None


def compile_with_esper(
    c_files: List[Path],
    output_bin: Optional[Path] = None,
    extra_flags: Optional[List[str]] = None,
) -> Optional[CompilationResult]:
    """Intenta compilar usando la biblioteca o CLI de ESPER."""
    out_target = str(output_bin) if output_bin else "/dev/null"
    flags = extra_flags or ["-Wall", "-Wextra", "-std=c11"]
    args = flags + [str(f) for f in c_files] + ["-o", out_target]

    # 1. Import directo de Python
    run_gcc_fn = _try_import_esper()
    if run_gcc_fn:
        try:
            report = run_gcc_fn(args)
            diags = []
            for d in report.diagnostics:
                sev = d.severity.value if hasattr(d.severity, "value") else str(d.severity)
                tr_msg = f"{d.title_es}: {d.explanation_es}" if d.title_es and d.explanation_es else (d.title_es or d.explanation_es or d.raw_message)
                diags.append({
                    "file": d.file_path,
                    "line": d.line_number,
                    "severity": sev.upper(),
                    "translated_message": tr_msg,
                    "suggestion": d.suggestion_es,
                    "raw_message": d.raw_message,
                    "code_snippet": d.code_snippet,
                })

            return CompilationResult(
                success=report.passed,
                output_bin=output_bin if report.passed and output_bin else None,
                raw_stderr=report.raw_stderr,
                translated_diagnostics=diags,
                compiler_used="esper",
            )
        except Exception:
            pass

    # 2. CLI de esper con --json
    esper_bin = shutil.which("esper") or (Path.home() / ".local" / "bin" / "esper" if (Path.home() / ".local" / "bin" / "esper").is_file() else None)
    if esper_bin:
        try:
            cmd = [str(esper_bin), "compile"] + args + ["--json"]
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if proc.stdout.strip():
                data = json.loads(proc.stdout)
                raw_diags = data.get("diagnostics", [])
                diags = []
                for d in raw_diags:
                    sev = str(d.get("severity", "ERROR")).upper()
                    t_es = d.get("title_es", "")
                    exp_es = d.get("explanation_es", "")
                    tr_msg = f"{t_es}: {exp_es}" if t_es and exp_es else (t_es or exp_es or d.get("raw_message", ""))
                    diags.append({
                        "file": d.get("file_path", ""),
                        "line": d.get("line_number", 1),
                        "severity": sev,
                        "translated_message": tr_msg,
                        "suggestion": d.get("suggestion_es", ""),
                        "raw_message": d.get("raw_message", ""),
                        "code_snippet": d.get("code_snippet"),
                    })
                passed = data.get("passed", proc.returncode == 0)
                return CompilationResult(
                    success=passed,
                    output_bin=output_bin if passed and output_bin else None,
                    raw_stderr=data.get("raw_stderr", proc.stderr),
                    translated_diagnostics=diags,
                    compiler_used="esper",
                )
        except Exception:
            pass

    return None


def compile_with_gcc(
    c_files: List[Path],
    output_bin: Optional[Path] = None,
    extra_flags: Optional[List[str]] = None,
) -> Optional[CompilationResult]:
    """Compila usando GCC directamente como mecanismo de fallback."""
    gcc = shutil.which("gcc")
    if not gcc:
        return None

    out_target = str(output_bin) if output_bin else "/dev/null"
    flags = extra_flags or ["-Wall", "-Wextra", "-std=c11"]
    cmd = [gcc] + flags + [str(f) for f in c_files] + ["-o", out_target]

    proc = subprocess.run(cmd, capture_output=True, text=True)
    return CompilationResult(
        success=(proc.returncode == 0),
        output_bin=output_bin if (proc.returncode == 0 and output_bin) else None,
        raw_stderr=proc.stderr,
        translated_diagnostics=[],
        compiler_used="gcc",
    )


def compile_c_sources(
    c_files: List[Path],
    output_bin: Optional[Path] = None,
    extra_flags: Optional[List[str]] = None,
) -> CompilationResult:
    """Compila archivos C utilizando prioritariamente ESPER, con fallback transparente a GCC."""
    if not c_files:
        return CompilationResult(
            success=False,
            raw_stderr="No se encontraron archivos .c para compilar.",
            compiler_used="none",
        )

    # 1. Intentar compilar con ESPER
    esper_res = compile_with_esper(c_files, output_bin=output_bin, extra_flags=extra_flags)
    if esper_res is not None:
        return esper_res

    # 2. Fallback a GCC
    gcc_res = compile_with_gcc(c_files, output_bin=output_bin, extra_flags=extra_flags)
    if gcc_res is not None:
        return gcc_res

    return CompilationResult(
        success=False,
        raw_stderr="Ni ESPER ni GCC se encuentran disponibles en el sistema.",
        compiler_used="none",
    )


def compile_with_make(
    build_dir: Path,
    target_name: Optional[str] = None,
    output_bin: Optional[Path] = None,
    extra_flags: Optional[List[str]] = None,
) -> CompilationResult:
    """Compila invocando make en build_dir para entregas basadas en Makefiles."""
    make = shutil.which("make")
    if not make:
        return CompilationResult(
            success=False,
            raw_stderr="La herramienta 'make' no se encuentra disponible en el sistema.",
            compiler_used="make",
        )

    makefile = build_dir / "Makefile"
    makefile_alt = build_dir / "makefile"
    if not makefile.is_file() and not makefile_alt.is_file():
        return CompilationResult(
            success=False,
            raw_stderr=f"No se encontró un archivo Makefile en '{build_dir}'.",
            compiler_used="make",
        )

    cmd = [make, "-C", str(build_dir)]
    if target_name:
        cmd.append(target_name)
    if extra_flags:
        cmd.extend(extra_flags)

    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        bin_found = None
        if output_bin and output_bin.is_file():
            bin_found = output_bin
        else:
            # Buscar binarios ejecutables generados
            import os
            for f in build_dir.iterdir():
                if f.is_file() and not f.name.endswith((".c", ".h", ".o", ".in", ".out", ".md", ".txt", ".yaml", ".json", ".db")):
                    if os.access(f, os.X_OK):
                        bin_found = f
                        break

        return CompilationResult(
            success=(proc.returncode == 0),
            output_bin=bin_found,
            raw_stderr=proc.stderr,
            translated_diagnostics=[],
            compiler_used="make",
        )
    except Exception as e:
        return CompilationResult(
            success=False,
            raw_stderr=f"Error durante la ejecución de make: {e}",
            compiler_used="make",
        )
