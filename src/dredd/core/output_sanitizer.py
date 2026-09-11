"""Módulo de sanitización de flujos de salida estándar y logs estudiantiles.

Filtra secuencias ANSI, caracteres de control corruptos y trunca salidas que excedan límites seguros.
"""

from __future__ import annotations

from pathlib import Path
import re
from typing import Optional, Union

# Expresión regular para secuencias de escape ANSI
ANSI_ESCAPE_RE = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")

# Caracteres de control ASCII que no sean \t (0x09), \n (0x0A) ni \r (0x0D)
CONTROL_CHAR_RE = re.compile(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]")

# Límite seguro por defecto: 10 MB
DEFAULT_MAX_BYTES = 10 * 1024 * 1024


def sanitize_output(
    data: Union[str, bytes],
    max_bytes: int = DEFAULT_MAX_BYTES,
    strip_ansi: bool = True,
    strip_control: bool = True,
) -> str:
    """Sanitiza flujos de salida o logs de estudiantes.

    Aplica truncado seguro de tamaño, suprime secuencias ANSI y remueve caracteres de control.
    """
    truncated = False
    if isinstance(data, bytes):
        if len(data) > max_bytes:
            data = data[:max_bytes]
            truncated = True
        text = data.decode("utf-8", errors="replace")
    else:
        encoded = data.encode("utf-8", errors="replace")
        if len(encoded) > max_bytes:
            text = encoded[:max_bytes].decode("utf-8", errors="replace")
            truncated = True
        else:
            text = data

    if strip_ansi:
        text = ANSI_ESCAPE_RE.sub("", text)

    if strip_control:
        text = CONTROL_CHAR_RE.sub("", text)

    if truncated:
        text += f"\n\n[AVISO: Salida truncada automáticamente. Superó el límite de seguridad de {max_bytes} bytes]\n"

    return text


def sanitize_log_file(
    file_path: Path,
    output_path: Optional[Path] = None,
    max_bytes: int = DEFAULT_MAX_BYTES,
) -> Path:
    """Lee y sanitiza un archivo de log en disco, guardando el resultado en output_path o sobre el mismo archivo."""
    target_out = output_path or file_path
    raw_content = file_path.read_bytes()
    sanitized_text = sanitize_output(raw_content, max_bytes=max_bytes)
    target_out.write_text(sanitized_text, encoding="utf-8")
    return target_out
