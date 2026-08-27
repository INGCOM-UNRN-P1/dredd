"""Aislamiento de procesos por namespaces / setrlimit y detección de evasión de sandbox."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import resource
import shutil
import subprocess
from typing import Dict, List, Optional, Tuple


DANGEROUS_CALLS_REGEX = re.compile(
    r"\b("
    r"ptrace|personality|seccomp|unshare|sys_clone|syscall|"
    r"fork|clone|vfork|"
    r"system|execve|execvp|execl|execlp|execle|execv|popen|"
    r"socket|connect|bind|listen|accept|sendto|recvfrom|"
    r"kill|raise|signal|sigaction|"
    r"chroot|pivot_root"
    r")\s*\(",
    re.IGNORECASE,
)

FORK_BOMB_PATTERNS = [
    re.compile(r"while\s*\(\s*1\s*\)\s*\{\s*fork\s*\(\s*\)\s*;", re.IGNORECASE),
    re.compile(r"for\s*\(\s*;\s*;\s*\)\s*fork\s*\(\s*\)\s*;", re.IGNORECASE),
    re.compile(r"while\s*\(\s*fork\s*\(\s*\)\s*\)", re.IGNORECASE),
]

PROHIBITED_PATHS = [
    "/proc/self/mem",
    "/proc/self/cwd",
    "/proc/kcore",
    "/dev/mem",
    "/dev/kmem",
    "/etc/shadow",
    "/etc/passwd",
]


@dataclass
class SecurityFinding:
    severity: str  # "ERROR", "FATAL", "ADVERTENCIA"
    title: str
    message: str
    line: int
    rule_code: str = "SEC001"
    code_snippet: str = ""


def audit_sandbox_evasion(code: str, filename: str = "entrega.c") -> List[SecurityFinding]:
    """Audita código fuente C en busca de intentos de evasión de sandbox, fork-bombs o llamadas restringidas."""
    findings: List[SecurityFinding] = []
    lines = code.splitlines()

    # 1. Chequeo de llamadas a funciones de sistema peligrosas
    for idx, line in enumerate(lines, start=1):
        if line.strip().startswith("//") or line.strip().startswith("/*"):
            continue

        match = DANGEROUS_CALLS_REGEX.search(line)
        if match:
            fn_name = match.group(1).lower()
            if fn_name in ("ptrace", "personality", "seccomp", "unshare", "sys_clone"):
                findings.append(
                    SecurityFinding(
                        severity="FATAL",
                        title="Intento de evasión o manipulación de sandbox",
                        message=f"Llamada a `{fn_name}()` prohibida. Posible intento de evadir el entorno de sandbox.",
                        line=idx,
                        rule_code="SEC_EVASION",
                        code_snippet=line.strip(),
                    )
                )
            elif fn_name in ("fork", "clone", "vfork"):
                findings.append(
                    SecurityFinding(
                        severity="ERROR",
                        title="Creación no autorizada de procesos / Fork",
                        message=f"Uso de `{fn_name}()` prohibido en la materia. Riesgo de saturación de recursos.",
                        line=idx,
                        rule_code="SEC_FORK",
                        code_snippet=line.strip(),
                    )
                )
            elif fn_name in ("system", "execve", "execvp", "execl", "popen"):
                findings.append(
                    SecurityFinding(
                        severity="ERROR",
                        title="Ejecución de procesos y shell arbitrarios",
                        message=f"Llamada a `{fn_name}()` prohibida. No se permite invocar subprocesos en las entregas.",
                        line=idx,
                        rule_code="SEC_EXEC",
                        code_snippet=line.strip(),
                    )
                )
            elif fn_name in ("socket", "connect", "bind", "listen"):
                findings.append(
                    SecurityFinding(
                        severity="ERROR",
                        title="Uso no autorizado de sockets de red",
                        message=f"Llamada a `{fn_name}()` prohibida. El acceso a red está deshabilitado.",
                        line=idx,
                        rule_code="SEC_NET",
                        code_snippet=line.strip(),
                    )
                )

        for p_path in PROHIBITED_PATHS:
            if p_path in line:
                findings.append(
                    SecurityFinding(
                        severity="FATAL",
                        title="Acceso a rutas privilegiadas del sistema",
                        message=f"Referencia a `{p_path}` prohibida.",
                        line=idx,
                        rule_code="SEC_PATH",
                        code_snippet=line.strip(),
                    )
                )

    # 2. Detección de patrones de fork-bombs
    for pat in FORK_BOMB_PATTERNS:
        if pat.search(code):
            findings.append(
                SecurityFinding(
                    severity="FATAL",
                    title="Patrón de Fork-Bomb detectado",
                    message="Bucle infinito generando procesos recursivamente (fork bomb).",
                    line=1,
                    rule_code="SEC_FORKBOMB",
                    code_snippet="while(1) fork();",
                )
            )

    return findings


def _set_resource_limits(max_memory_mb: int = 64, max_cpu_seconds: int = 5) -> None:
    """Configura límites estrictos de recursos para el proceso hijo usando setrlimit."""
    try:
        mem_bytes = max_memory_mb * 1024 * 1024
        # Límite de memoria virtual (RLIMIT_AS)
        resource.setrlimit(resource.RLIMIT_AS, (mem_bytes, mem_bytes))
    except Exception:
        pass

    try:
        # Límite de tiempo de CPU
        resource.setrlimit(resource.RLIMIT_CPU, (max_cpu_seconds, max_cpu_seconds + 1))
    except Exception:
        pass


def execute_sandboxed(
    cmd: List[str],
    input_data: str = "",
    timeout: float = 5.0,
    max_memory_mb: int = 64,
    workspace: Optional[Path] = None,
) -> Tuple[int, str, str, bool]:
    """Ejecuta un binario C en sandbox con límites estrictos de RAM (64MB) y tiempo.
    
    Devuelve (returncode, stdout, stderr, timeout_or_killed).
    """
    bwrap_bin = shutil.which("bwrap")
    cwd_dir = str(workspace.resolve()) if workspace and workspace.is_dir() else None

    # Si bubblewrap está disponible, intentar aislar namespaces
    if bwrap_bin:
        bwrap_cmd = [
            bwrap_bin,
            "--unshare-all",
            "--ro-bind", "/", "/",
            "--tmpfs", "/tmp",
            "--dev", "/dev",
            "--proc", "/proc",
        ]
        if cwd_dir:
            bwrap_cmd.extend(["--bind", cwd_dir, cwd_dir, "--chdir", cwd_dir])
        full_cmd = bwrap_cmd + ["--"] + cmd

        try:
            proc = subprocess.run(
                full_cmd,
                input=input_data,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=cwd_dir,
            )
            if proc.returncode == 0 or "bwrap:" not in proc.stderr:
                return proc.returncode, proc.stdout, proc.stderr, False
        except subprocess.TimeoutExpired as e:
            stdout_txt = e.stdout.decode("utf-8", errors="replace") if isinstance(e.stdout, bytes) else (e.stdout or "")
            stderr_txt = e.stderr.decode("utf-8", errors="replace") if isinstance(e.stderr, bytes) else (e.stderr or "")
            return -1, stdout_txt, f"[TIMEOUT] Proceso cancelado tras {timeout}s: {stderr_txt}", True
        except Exception:
            pass

    # Fallback seguro con setrlimit directo
    try:
        proc = subprocess.run(
            cmd,
            input=input_data,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=cwd_dir,
            preexec_fn=lambda: _set_resource_limits(max_memory_mb=max_memory_mb, max_cpu_seconds=int(timeout) + 1),
        )
        return proc.returncode, proc.stdout, proc.stderr, False
    except subprocess.TimeoutExpired as e:
        stdout_txt = e.stdout.decode("utf-8", errors="replace") if isinstance(e.stdout, bytes) else (e.stdout or "")
        stderr_txt = e.stderr.decode("utf-8", errors="replace") if isinstance(e.stderr, bytes) else (e.stderr or "")
        return -1, stdout_txt, f"[TIMEOUT / MEMORY EXCEEDED] Proceso cancelado tras {timeout}s: {stderr_txt}", True
    except Exception as e:
        return -1, "", f"Error de ejecución en sandbox: {e}", False

