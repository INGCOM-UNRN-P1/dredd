"""Módulo de análisis de memoria con Valgrind y AddressSanitizer para Dredd."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class ValgrindError:
    kind: str  # "InvalidRead", "InvalidWrite", "UseAfterFree", "UninitializedValue", "Leak", "Other"
    message: str
    location: str = ""
    raw_stack: str = ""


@dataclass
class ValgrindReport:
    executed: bool = False
    clean: bool = True
    definitely_lost_bytes: int = 0
    definitely_lost_blocks: int = 0
    indirectly_lost_bytes: int = 0
    indirectly_lost_blocks: int = 0
    possibly_lost_bytes: int = 0
    possibly_lost_blocks: int = 0
    still_reachable_bytes: int = 0
    still_reachable_blocks: int = 0
    total_errors: int = 0
    errors: List[ValgrindError] = field(default_factory=list)
    raw_output: str = ""
    timed_out: bool = False

    @property
    def has_leaks(self) -> bool:
        return (self.definitely_lost_bytes > 0) or (self.indirectly_lost_bytes > 0) or (self.possibly_lost_bytes > 0)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "executed": self.executed,
            "clean": self.clean,
            "has_leaks": self.has_leaks,
            "definitely_lost_bytes": self.definitely_lost_bytes,
            "definitely_lost_blocks": self.definitely_lost_blocks,
            "indirectly_lost_bytes": self.indirectly_lost_bytes,
            "indirectly_lost_blocks": self.indirectly_lost_blocks,
            "possibly_lost_bytes": self.possibly_lost_bytes,
            "possibly_lost_blocks": self.possibly_lost_blocks,
            "still_reachable_bytes": self.still_reachable_bytes,
            "still_reachable_blocks": self.still_reachable_blocks,
            "total_errors": self.total_errors,
            "errors": [
                {"kind": e.kind, "message": e.message, "location": e.location, "raw_stack": e.raw_stack}
                for e in self.errors
            ],
            "raw_output": self.raw_output,
            "timed_out": self.timed_out,
        }


def parse_valgrind_output(output: str) -> ValgrindReport:
    """Parsea el log de Valgrind Memcheck y extrae métricas de leaks y errores."""
    report = ValgrindReport(executed=True, raw_output=output)

    # 1. Leaks
    m_def = re.search(r"definitely lost:\s*([\d,]+)\s*bytes in\s*([\d,]+)\s*blocks", output, re.IGNORECASE)
    if m_def:
        report.definitely_lost_bytes = int(m_def.group(1).replace(",", ""))
        report.definitely_lost_blocks = int(m_def.group(2).replace(",", ""))

    m_ind = re.search(r"indirectly lost:\s*([\d,]+)\s*bytes in\s*([\d,]+)\s*blocks", output, re.IGNORECASE)
    if m_ind:
        report.indirectly_lost_bytes = int(m_ind.group(1).replace(",", ""))
        report.indirectly_lost_blocks = int(m_ind.group(2).replace(",", ""))

    m_pos = re.search(r"possibly lost:\s*([\d,]+)\s*bytes in\s*([\d,]+)\s*blocks", output, re.IGNORECASE)
    if m_pos:
        report.possibly_lost_bytes = int(m_pos.group(1).replace(",", ""))
        report.possibly_lost_blocks = int(m_pos.group(2).replace(",", ""))

    m_reach = re.search(r"still reachable:\s*([\d,]+)\s*bytes in\s*([\d,]+)\s*blocks", output, re.IGNORECASE)
    if m_reach:
        report.still_reachable_bytes = int(m_reach.group(1).replace(",", ""))
        report.still_reachable_blocks = int(m_reach.group(2).replace(",", ""))

    # 2. Resumen de errores
    m_err = re.search(r"ERROR SUMMARY:\s*(\d+)\s*errors", output, re.IGNORECASE)
    if m_err:
        report.total_errors = int(m_err.group(1))

    # 3. Clasificar errores específicos
    for line in output.splitlines():
        line_clean = re.sub(r"^==\d+==\s*", "", line).strip()
        if "Invalid read of size" in line_clean:
            report.errors.append(ValgrindError(kind="InvalidRead", message=line_clean))
        elif "Invalid write of size" in line_clean:
            report.errors.append(ValgrindError(kind="InvalidWrite", message=line_clean))
        elif "Conditional jump or move depends on uninitialised value" in line_clean:
            report.errors.append(ValgrindError(kind="UninitializedValue", message=line_clean))
        elif "Use of uninitialised value" in line_clean:
            report.errors.append(ValgrindError(kind="UninitializedValue", message=line_clean))
        elif "Mismatched free() / delete / delete []" in line_clean:
            report.errors.append(ValgrindError(kind="MismatchedFree", message=line_clean))
        elif "Source and destination overlap" in line_clean:
            report.errors.append(ValgrindError(kind="Overlap", message=line_clean))

    report.clean = (report.total_errors == 0) and not report.has_leaks
    return report


def run_valgrind_check(
    cmd: List[str],
    input_data: str = "",
    timeout: float = 6.0,
    workspace: Optional[Path] = None,
) -> ValgrindReport:
    """Ejecuta un comando con Valgrind Memcheck y retorna el reporte parseado."""
    valgrind_bin = shutil.which("valgrind")
    if not valgrind_bin:
        return ValgrindReport(executed=False, raw_output="Valgrind no está instalado en el sistema.")

    with tempfile.NamedTemporaryFile(suffix=".log", delete=False) as tmp_log:
        log_path = Path(tmp_log.name)

    val_cmd = [
        valgrind_bin,
        "--leak-check=full",
        "--show-leak-kinds=all",
        "--track-origins=yes",
        "--error-exitcode=42",
        f"--log-file={log_path}",
    ] + cmd

    cwd_dir = str(workspace.resolve()) if workspace and workspace.is_dir() else None

    try:
        proc = subprocess.run(
            val_cmd,
            input=input_data,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=cwd_dir,
        )
        raw_log = log_path.read_text(encoding="utf-8", errors="replace") if log_path.is_file() else ""
        report = parse_valgrind_output(raw_log)
        return report
    except subprocess.TimeoutExpired:
        raw_log = log_path.read_text(encoding="utf-8", errors="replace") if log_path.is_file() else ""
        report = parse_valgrind_output(raw_log)
        report.timed_out = True
        report.clean = False
        return report
    except Exception as e:
        return ValgrindReport(executed=False, raw_output=f"Error ejecutando Valgrind: {e}")
    finally:
        if log_path.is_file():
            try:
                log_path.unlink()
            except Exception:
                pass
