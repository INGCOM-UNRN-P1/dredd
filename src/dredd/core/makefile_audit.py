"""Auditor de seguridad, dependencias no autorizadas y trampas en archivos Makefile."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import List, Optional, Set

LIBRERIAS_PERMITIDAS_DEFAULT: Set[str] = {
    "m",          # Math
    "pthread",    # POSIX Threads
    "rt",         # Realtime
    "p1_test",    # Framework cátedra
    "check",      # Check C testing
}


@dataclass
class FindingMakefile:
    severidad: str  # "ERROR", "ADVERTENCIA", "TRAMPA"
    linea: int
    regla: str
    mensaje: str
    codigo: str

    def to_dict(self) -> dict:
        return {
            "severidad": self.severidad,
            "linea": self.linea,
            "regla": self.regla,
            "mensaje": self.mensaje,
            "codigo": self.codigo,
        }


def auditar_makefile(
    ruta_makefile: Path,
    librerias_permitidas: Optional[Set[str]] = None,
) -> List[FindingMakefile]:
    """Inspecciona un Makefile en busca de dependencias prohibidas y evasiones de compilación."""
    if not ruta_makefile.is_file():
        return []

    contenido = ruta_makefile.read_text(encoding="utf-8", errors="replace")
    lineas = contenido.splitlines()

    permitidas = librerias_permitidas or LIBRERIAS_PERMITIDAS_DEFAULT
    findings: List[FindingMakefile] = []

    for num, linea in enumerate(lineas, start=1):
        linea_strip = linea.strip()
        if not linea_strip or linea_strip.startswith("#"):
            continue

        # 1. Detección de trampas: supresión total de warnings con -w o flags deshabilitadoras
        if re.search(r"(?:^|\s)-w(?:\s|$)", linea_strip) or "-Wno-all" in linea_strip:
            findings.append(FindingMakefile(
                severidad="TRAMPA",
                linea=num,
                regla="MK_DISABLE_WARNINGS",
                mensaje="Uso de flag '-w' o '-Wno-all' para silenciar advertencias del compilador.",
                codigo=linea_strip,
            ))

        # 2. Detección de enmascaramiento de errores (|| true, || exit 0, etc.)
        if re.search(r"\|\|\s*(true|exit\s*0|:)", linea_strip):
            findings.append(FindingMakefile(
                severidad="TRAMPA",
                linea=num,
                regla="MK_MASK_ERRORS",
                mensaje="Enmascaramiento de código de salida con '|| true' o '|| exit 0'.",
                codigo=linea_strip,
            ))

        # 3. Detección de descarga o invocación de red en Makefile
        if re.search(r"\b(curl|wget|git\s+clone|nc|ssh)\b", linea_strip):
            findings.append(FindingMakefile(
                severidad="ERROR",
                linea=num,
                regla="MK_NETWORK_DOWNLOAD",
                mensaje="Comando de red o descarga externa detectado dentro del Makefile.",
                codigo=linea_strip,
            ))

        # 4. Copia o uso de binarios precompilados (.o, .a, ejecutables existentes)
        if re.search(r"\bcp\s+.*?\.(o|a|so|dll)\b", linea_strip) or re.search(r"\bcp\s+.*?bin\b", linea_strip):
            findings.append(FindingMakefile(
                severidad="TRAMPA",
                linea=num,
                regla="MK_PRECOMPILED_COPY",
                mensaje="Copia de artefactos o binarios precompilados detectada en reglas de compilación.",
                codigo=linea_strip,
            ))

        # 5. Auditoría de bibliotecas externas vinculadas con -l<nombre>
        flags_libs = re.findall(r"-l([a-zA-Z0-9_\-]+)", linea_strip)
        for lib in flags_libs:
            if lib.lower() not in permitidas:
                findings.append(FindingMakefile(
                    severidad="ERROR",
                    linea=num,
                    regla="MK_UNAUTHORIZED_LIB",
                    mensaje=f"Vinculación con biblioteca externa no autorizada: '-l{lib}'.",
                    codigo=linea_strip,
                ))

        # 6. Sobrescritura no estándar del compilador CC con ejecutables ocultos
        if re.match(r"^\s*CC\s*[:?]?=\s*(\./|\.\./|bash|sh|python)", linea_strip):
            findings.append(FindingMakefile(
                severidad="TRAMPA",
                linea=num,
                regla="MK_SUSPICIOUS_COMPILER",
                mensaje="Definición de variable CC apuntando a scripts o rutas locales arbitrarias.",
                codigo=linea_strip,
            ))

    return findings
