"""Aislamiento de procesos por namespaces / setrlimit y detección de evasión de sandbox."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os
import re
import resource
import shutil
import subprocess
from typing import Dict, List, Optional, Tuple

from dredd.core.output_sanitizer import sanitize_output


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


def strip_c_comments_and_strings(code: str) -> str:
    """Elimina comentarios y cadenas literales manteniendo los saltos de línea para conservar número de línea."""

    def replacer(match: re.Match) -> str:
        s = match.group(0)
        if s.startswith("/"):
            # Reemplazar comentarios por espacios en blanco preservando '\n'
            return re.sub(r"[^\n]", " ", s)
        else:
            # String o char literal
            return '""' + re.sub(r"[^\n]", " ", s[2:])

    pattern = re.compile(
        r'//.*?$|/\*.*?\*/|\'(?:\\.|[^\\\'])*\'|"(?:\\.|[^\\"])*"',
        re.DOTALL | re.MULTILINE,
    )
    return re.sub(pattern, replacer, code)


def audit_sandbox_evasion(code: str, filename: str = "entrega.c") -> List[SecurityFinding]:
    """Audita código fuente C en busca de intentos de evasión de sandbox, fork-bombs o llamadas restringidas."""
    findings: List[SecurityFinding] = []
    clean_code = strip_c_comments_and_strings(code)
    clean_lines = clean_code.splitlines()
    orig_lines = code.splitlines()

    # 1. Chequeo de llamadas a funciones de sistema peligrosas
    for idx, line in enumerate(clean_lines, start=1):
        orig_line = orig_lines[idx - 1] if idx - 1 < len(orig_lines) else line

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
                        code_snippet=orig_line.strip(),
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
                        code_snippet=orig_line.strip(),
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
                        code_snippet=orig_line.strip(),
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
                        code_snippet=orig_line.strip(),
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
                        code_snippet=orig_line.strip(),
                    )
                )

    # 2. Detección de patrones de fork-bombs
    for pat in FORK_BOMB_PATTERNS:
        if pat.search(clean_code):
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


def _try_import_nostromo():
    try:
        from nostromo.core.sandbox import ejecutar_aislado
    except ImportError:
        return None  # sin el extra `ecosistema` se usa el camino propio
    return ejecutar_aislado


# ── Construcción del sandbox bubblewrap ──────────────────────────────────────
#
# Dentro del sandbox solo se ve lo imprescindible para ejecutar un binario C:
# los directorios del sistema (solo lectura), el directorio del ejecutable
# (solo lectura) y el workspace de la entrega (lectura y escritura). Nunca se
# monta `/` completo: eso exponía a la entrega el HOME del docente (soluciones
# canónicas, entregas de otros estudiantes, claves).

_DIRECTORIOS_DEL_SISTEMA = ("/usr", "/lib", "/lib64", "/bin", "/sbin")

# Ejecutar la entrega sin ningún aislamiento de sistema de archivos solo se
# permite si quien corre dredd lo autoriza explícitamente.
ENV_PERMITIR_SIN_SANDBOX = "DREDD_PERMITIR_SIN_SANDBOX"

MENSAJE_SIN_SANDBOX = (
    "No se ejecutó la entrega: no hay un sandbox disponible (bubblewrap no está "
    "instalado o no funciona en este sistema, y nostromo no está instalado). "
    "Instalá bubblewrap (`sudo apt install bubblewrap` / `sudo dnf install bubblewrap`) "
    f"o, bajo tu responsabilidad, exportá {ENV_PERMITIR_SIN_SANDBOX}=1 para ejecutar "
    "sin aislamiento (el código del estudiante tendrá acceso a tus archivos)."
)

_FLAGS_AISLAMIENTO_CACHE: Optional[List[str]] = None


def _binds_del_sistema(existe=os.path.exists) -> List[str]:
    """`--ro-bind` de cada directorio del sistema que existe (bwrap aborta si falta el origen)."""
    args: List[str] = []
    for directorio in _DIRECTORIOS_DEL_SISTEMA:
        if existe(directorio):
            args += ["--ro-bind", directorio, directorio]
    return args


def _flags_aislamiento(bwrap_bin: str, requerir_red_aislada: bool) -> Optional[List[str]]:
    """Banderas de namespaces que funcionan en este host, o None si ninguna sirve.

    `--unshare-all` también aísla la red; en contenedores sin CAP_NET_ADMIN falla
    al configurar loopback. En ese caso, si no se exige red aislada, se aíslan
    user/IPC/PID/UTS sin tocar la red (mismo criterio que nostromo).
    """
    global _FLAGS_AISLAMIENTO_CACHE
    if _FLAGS_AISLAMIENTO_CACHE is None:
        candidatos = [
            ["--unshare-all"],
            ["--unshare-user", "--unshare-ipc", "--unshare-pid", "--unshare-uts", "--unshare-cgroup-try"],
        ]
        _FLAGS_AISLAMIENTO_CACHE = []
        for flags in candidatos:
            try:
                res = subprocess.run(
                    [bwrap_bin, *flags, *_binds_del_sistema(), "--proc", "/proc", "--dev", "/dev", "true"],
                    capture_output=True,
                    timeout=5.0,
                    check=False,
                )
            except (OSError, subprocess.SubprocessError):
                continue
            if res.returncode == 0:
                _FLAGS_AISLAMIENTO_CACHE = flags
                break
    if not _FLAGS_AISLAMIENTO_CACHE:
        return None
    if requerir_red_aislada and "--unshare-all" not in _FLAGS_AISLAMIENTO_CACHE:
        return None
    return list(_FLAGS_AISLAMIENTO_CACHE)


def _comando_bwrap(
    bwrap_bin: str,
    cmd: List[str],
    cwd_dir: Optional[str],
    flags: List[str],
    extra: Optional[List[str]] = None,
) -> List[str]:
    """Arma el comando bwrap con montajes mínimos para ejecutar `cmd`.

    El orden importa: `--tmpfs /tmp` va antes de montar el ejecutable y el
    workspace para no ocultarlos cuando viven bajo /tmp.
    """
    args = [bwrap_bin, *flags, *_binds_del_sistema(), "--tmpfs", "/tmp", "--dev", "/dev", "--proc", "/proc"]
    args += list(extra or [])
    # Un nombre sin separador (p. ej. "echo") se busca en el PATH dentro del
    # sandbox; una ruta relativa se interpreta desde el workspace.
    ejecutable = Path(cmd[0]) if cmd and os.sep in cmd[0] else None
    if ejecutable is not None and not ejecutable.is_absolute() and cwd_dir:
        ejecutable = Path(cwd_dir) / ejecutable
    if ejecutable is not None and ejecutable.is_file():
        directorio = str(ejecutable.resolve().parent)
        if not (cwd_dir and (directorio == cwd_dir or directorio.startswith(cwd_dir + os.sep))):
            args += ["--ro-bind", directorio, directorio]
        cmd = [str(ejecutable.resolve())] + list(cmd[1:])
    if cwd_dir:
        args += ["--bind", cwd_dir, cwd_dir, "--chdir", cwd_dir]
    return args + ["--die-with-parent", "--"] + list(cmd)


def _decodificar(valor) -> str:
    if isinstance(valor, bytes):
        return valor.decode("utf-8", errors="replace")
    return valor or ""


def _ejecutar_con_bwrap(
    full_cmd: List[str],
    input_data: str,
    timeout: float,
    cwd_dir: Optional[str],
    etiqueta_timeout: str,
) -> Optional[Tuple[int, str, str, bool]]:
    """Corre el comando ya envuelto en bwrap; devuelve None si bwrap no pudo armar el sandbox."""
    try:
        proc = subprocess.run(
            full_cmd,
            input=input_data,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=cwd_dir,
        )
    except subprocess.TimeoutExpired as e:
        return -1, sanitize_output(_decodificar(e.stdout)), sanitize_output(
            f"[{etiqueta_timeout}] Proceso cancelado tras {timeout}s: {_decodificar(e.stderr)}"
        ), True
    except OSError:
        return None
    if proc.returncode != 0 and proc.stderr.startswith("bwrap:"):
        return None
    return proc.returncode, sanitize_output(proc.stdout), sanitize_output(proc.stderr), False


def _sin_sandbox_permitido() -> bool:
    return os.environ.get(ENV_PERMITIR_SIN_SANDBOX, "").strip().lower() in ("1", "true", "si", "sí", "yes")


def _ejecutar_sin_aislamiento(
    cmd: List[str],
    input_data: str,
    timeout: float,
    cwd_dir: Optional[str],
    limites,
    etiqueta_timeout: str,
) -> Tuple[int, str, str, bool]:
    """Solo con autorización explícita: límites de recursos, sin aislamiento de archivos."""
    if not _sin_sandbox_permitido():
        return -1, "", MENSAJE_SIN_SANDBOX, False
    try:
        proc = subprocess.run(
            cmd,
            input=input_data,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=cwd_dir,
            preexec_fn=limites,
        )
        return proc.returncode, sanitize_output(proc.stdout), sanitize_output(proc.stderr), False
    except subprocess.TimeoutExpired as e:
        return -1, sanitize_output(_decodificar(e.stdout)), sanitize_output(
            f"[{etiqueta_timeout}] Proceso cancelado tras {timeout}s: {_decodificar(e.stderr)}"
        ), True
    except Exception as e:
        return -1, "", f"Error de ejecución en sandbox: {e}", False


def execute_sandboxed(
    cmd: List[str],
    input_data: str = "",
    timeout: float = 5.0,
    max_memory_mb: int = 64,
    workspace: Optional[Path] = None,
) -> Tuple[int, str, str, bool]:
    """Ejecuta un binario C en sandbox delegando en nostromo, o con bubblewrap propio.

    Sin nostromo ni bubblewrap funcional la entrega no se ejecuta, salvo que se
    exporte DREDD_PERMITIR_SIN_SANDBOX=1 (entonces corre solo con setrlimit).

    Devuelve (returncode, stdout, stderr, timeout_or_killed).
    """
    nostromo_fn = _try_import_nostromo()
    if nostromo_fn and cmd:
        bin_path = Path(cmd[0])
        res = nostromo_fn(
            bin_path,
            args=cmd[1:],
            stdin_texto=input_data,
            timeout_segundos=timeout,
            memoria_mb=max_memory_mb,
            usar_bwrap=True,
        )
        is_timed_out = res.error_tipo == "TIMEOUT"
        return res.codigo_retorno, sanitize_output(res.stdout), sanitize_output(res.stderr), is_timed_out

    bwrap_bin = shutil.which("bwrap")
    cwd_dir = str(workspace.resolve()) if workspace and workspace.is_dir() else None

    if bwrap_bin and cmd:
        flags = _flags_aislamiento(bwrap_bin, requerir_red_aislada=False)
        if flags is not None:
            resultado = _ejecutar_con_bwrap(
                _comando_bwrap(bwrap_bin, cmd, cwd_dir, flags), input_data, timeout, cwd_dir, "TIMEOUT"
            )
            if resultado is not None:
                return resultado

    return _ejecutar_sin_aislamiento(
        cmd,
        input_data,
        timeout,
        cwd_dir,
        lambda: _set_resource_limits(max_memory_mb=max_memory_mb, max_cpu_seconds=int(timeout) + 1),
        "TIMEOUT / MEMORY EXCEEDED",
    )


def _set_shielded_resource_limits(max_memory_mb: int = 48, max_cpu_seconds: int = 3, max_nofile: int = 16) -> None:
    """Configura límites reforzados de recursos, descriptores de archivos y memoria virtual."""
    _set_resource_limits(max_memory_mb=max_memory_mb, max_cpu_seconds=max_cpu_seconds)
    try:
        # Límite de descriptores de archivo abiertos para mitigar agotamiento de handles
        resource.setrlimit(resource.RLIMIT_NOFILE, (max_nofile, max_nofile))
    except Exception:
        pass
    try:
        # Límite de tamaño de stack
        stack_bytes = 8 * 1024 * 1024  # 8MB max
        resource.setrlimit(resource.RLIMIT_STACK, (stack_bytes, stack_bytes))
    except Exception:
        pass


def execute_shielded_sandbox(
    cmd: List[str],
    input_data: str = "",
    timeout: float = 3.0,
    max_memory_mb: int = 48,
    workspace: Optional[Path] = None,
) -> Tuple[int, str, str, bool]:
    """Modo 'Sandbox Blindado': namespaces completos (incluida la red), /tmp y /dev/shm propios.

    A diferencia de `execute_sandboxed`, exige red aislada: si el host no permite
    `--unshare-all`, no degrada a un aislamiento menor. Sin sandbox la entrega
    no se ejecuta, salvo DREDD_PERMITIR_SIN_SANDBOX=1.
    """
    bwrap_bin = shutil.which("bwrap")
    cwd_dir = str(workspace.resolve()) if workspace and workspace.is_dir() else None

    if bwrap_bin and cmd:
        flags = _flags_aislamiento(bwrap_bin, requerir_red_aislada=True)
        if flags is not None:
            full_cmd = _comando_bwrap(bwrap_bin, cmd, cwd_dir, flags, extra=["--tmpfs", "/dev/shm"])
            resultado = _ejecutar_con_bwrap(full_cmd, input_data, timeout, cwd_dir, "TIMEOUT BLINDADO")
            if resultado is not None:
                return resultado

    return _ejecutar_sin_aislamiento(
        cmd,
        input_data,
        timeout,
        cwd_dir,
        lambda: _set_shielded_resource_limits(max_memory_mb=max_memory_mb, max_cpu_seconds=int(timeout) + 1),
        "TIMEOUT / CGROUP OVERFLOW",
    )
