"""Módulo de detección, auditoría y purga de archivos binarios en entregas de estudiantes."""

from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Set, Tuple

PROHIBITED_BINARY_EXTENSIONS = {
    ".o",
    ".obj",
    ".a",
    ".lib",
    ".exe",
    ".out",
    ".bin",
    ".elf",
    ".com",
    ".so",
    ".dll",
    ".dylib",
    ".class",
    ".pyc",
    ".gch",
    ".pch",
}

BINARY_MAGIC_SIGNATURES: List[Tuple[bytes, str]] = [
    (b"\x7fELF", "Formato ejecutable o archivo objeto Linux ELF"),
    (b"MZ", "Formato ejecutable Windows PE (.exe / .dll)"),
    (b"!<arch>\n", "Biblioteca estática Unix ar (.a)"),
    (b"\xfe\xed\xfa\xce", "Binario Mach-O 32-bit"),
    (b"\xfe\xed\xfa\xcf", "Binario Mach-O 64-bit"),
    (b"\xce\xfa\xed\xfe", "Binario Mach-O 32-bit (little-endian)"),
    (b"\xcf\xfa\xed\xfe", "Binario Mach-O 64-bit (little-endian)"),
    (b"\xca\xfe\xba\xbe", "Binario Mach-O Fat / Java Class"),
    (b"\x00asm", "Binario WebAssembly"),
]


def is_binary_file(filename: str, raw_bytes: Optional[bytes] = None) -> Tuple[bool, str]:
    """Determina si un archivo es un binario precompilado o ejecutable por extensión o contenido."""
    ext = Path(filename).suffix.lower()
    if ext in PROHIBITED_BINARY_EXTENSIONS:
        return True, f"Extensión binaria prohibida '{ext}'"

    if raw_bytes is not None and len(raw_bytes) > 0:
        for magic, desc in BINARY_MAGIC_SIGNATURES:
            if raw_bytes.startswith(magic):
                return True, f"Firma binaria ejecutable detectada ({desc})"

        # Heurística de bytes nulos para archivos sin extensión o binarios arbitrarios
        # Se omiten archivos de compresión estándar
        if b"\x00" in raw_bytes[:1024] and ext not in (".zip", ".tar", ".gz", ".tgz", ".bz2", ".7z"):
            return True, "Contenido binario no textual (caracteres nulos detectados)"

    return False, ""


def _hallazgo_binario(rel_path: str, reason: str) -> Dict[str, Any]:
    return {
        "rule_code": "0x000Fh",
        "rule_id": "P1_BINARY_PROHIBITED",
        "rule_name": "[SEGURIDAD] Archivo binario no permitido en entrega",
        "file": rel_path,
        "line": 1,
        "severity": "ERROR",
        "message": (
            f"Se detectó y filtró el archivo binario prohibido '{rel_path}' ({reason}). "
            "Las entregas deben contener exclusivamente código fuente editable y makefiles."
        ),
        "suggestion": (
            "Eliminá todos los archivos binarios (.o, .a, .exe, etc.) antes de entregar. "
            "Ejecutá 'make clean' y agregá estas extensiones a tu .gitignore."
        ),
    }


def _muestra_del_indice(repo: Path, rel_path: str) -> Optional[bytes]:
    import subprocess

    try:
        proc = subprocess.run(["git", "-C", str(repo), "cat-file", "blob", f":{rel_path}"],
                              capture_output=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return None
    return proc.stdout[:1024] if proc.returncode == 0 else None


def _archivos_entregados(target_path: Path) -> Optional[Set[str]]:
    """Las rutas (relativas a `target_path`) que el alumno entregó, o None si no se puede saber.

    Lo que hay en disco no alcanza: el `make` de una corrida anterior de dredd (o del propio
    alumno) deja .o, .a y ejecutables sin versionar, y antes cada re-evaluación los informaba
    como binarios entregados. En un repo git cuenta lo versionado; en una entrega de Moodle, la
    ingesta ya filtró los binarios del ZIP y los registró en `.metadata.db` (de ahí los informa
    `_collect_binary_findings`), así que lo que aparezca en disco es de una compilación.
    """
    import subprocess

    if (target_path / ".git").exists():  # la raíz del repo del alumno, no un workspace versionado
        try:
            proc = subprocess.run(["git", "-C", str(target_path), "ls-files", "-z"],
                                  capture_output=True, timeout=30)
        except (OSError, subprocess.SubprocessError):
            proc = None
        if proc is not None and proc.returncode == 0:
            return {r for r in proc.stdout.decode("utf-8", errors="replace").split("\0") if r}
    if any((d / ".metadata.db").is_file() for d in (target_path, target_path.parent)):
        return set()
    return None


def audit_and_purge_binaries_from_dir(target_path: Path) -> List[Dict[str, Any]]:
    """Escanea un directorio de entrega, purga archivos binarios del disco y retorna la lista de hallazgos.

    Se purgan todos (para que no se usen binarios ajenos al compilar), pero sólo se informan los
    que el alumno entregó (ver `_archivos_entregados`).
    """
    findings: List[Dict[str, Any]] = []
    if not target_path.exists():
        return findings
    entregados = _archivos_entregados(target_path)
    informados: Set[str] = set()

    all_files = [f for f in target_path.glob("**/*") if f.is_file() and not any(p.startswith(".") for p in f.parts)]

    for f in all_files:
        try:
            sample = f.read_bytes()[:1024]
        except Exception:
            sample = None

        is_bin, reason = is_binary_file(f.name, sample)
        if is_bin:
            try:
                rel_path = f.relative_to(target_path).as_posix()
            except ValueError:
                rel_path = f.name

            if entregados is None or rel_path in entregados:
                findings.append(_hallazgo_binario(rel_path, reason))
                informados.add(rel_path)

            # Purgar el archivo del disco para que el compilador no use binarios ajenos
            try:
                f.unlink(missing_ok=True)
            except Exception:
                pass

    # Un binario versionado que una corrida anterior ya purgó del disco sigue en el repo: se lee
    # del índice para que la re-evaluación no lo pierda.
    for rel_path in sorted((entregados or set()) - informados):
        if (target_path / rel_path).exists():
            continue
        is_bin, reason = is_binary_file(Path(rel_path).name, _muestra_del_indice(target_path, rel_path))
        if is_bin:
            findings.append(_hallazgo_binario(rel_path, reason))

    return findings
