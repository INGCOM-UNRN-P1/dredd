"""Clasificador automático de tipologías de entrega de código en C."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
import re
from typing import Dict, List, Set


class TipoEntrega(str, Enum):
    MONOLITICA = "monolitica"
    MODULAR = "modular"
    LIBRERIA_TDA = "libreria_tda"
    INCOMPLETA = "incompleta"


@dataclass
class TipologiaReport:
    estudiante_o_dir: str
    tipologia: TipoEntrega
    cant_c: int
    cant_h: int
    total_loc: int
    tiene_main: bool
    tiene_makefile: bool
    archivos_c: List[str]
    archivos_h: List[str]
    diagnostico: str

    def to_dict(self) -> dict:
        return {
            "estudiante_o_dir": self.estudiante_o_dir,
            "tipologia": self.tipologia.value,
            "cant_c": self.cant_c,
            "cant_h": self.cant_h,
            "total_loc": self.total_loc,
            "tiene_main": self.tiene_main,
            "tiene_makefile": self.tiene_makefile,
            "archivos_c": self.archivos_c,
            "archivos_h": self.archivos_h,
            "diagnostico": self.diagnostico,
        }


def clasificar_tipologia_entrega(directorio_entrega: Path) -> TipologiaReport:
    """Clasifica el estilo arquitectónico de la entrega (monolítica, modular, librería o incompleta)."""
    dir_path = Path(directorio_entrega)
    archivos_c = sorted([f for f in dir_path.rglob("*.c") if ".git" not in f.parts and "tests" not in f.parts])
    archivos_h = sorted([f for f in dir_path.rglob("*.h") if ".git" not in f.parts])
    tiene_makefile = (dir_path / "Makefile").is_file() or (dir_path / "makefile").is_file()

    total_loc = 0
    tiene_main = False
    headers_incluidos: Set[str] = set()

    for c_file in archivos_c:
        try:
            txt = c_file.read_text(encoding="utf-8", errors="replace")
            total_loc += len(txt.splitlines())
            if re.search(r"\bint\s+main\s*\(", txt):
                tiene_main = True
            for inc in re.findall(r'#include\s+"([^"]+)"', txt):
                headers_incluidos.add(Path(inc).name)
        except Exception:
            pass

    cant_c = len(archivos_c)
    cant_h = len(archivos_h)

    # Evaluación de tipología
    if cant_c == 0:
        tipo = TipoEntrega.INCOMPLETA
        diag = "No se encontraron archivos fuentes C en la entrega."
    elif cant_c == 1 and cant_h == 0 and tiene_main:
        tipo = TipoEntrega.MONOLITICA
        diag = "Código monolítico en un único archivo C que contiene todo el flujo y la función main()."
    elif cant_c > 1 and cant_h >= 1 and tiene_main:
        tipo = TipoEntrega.MODULAR
        diag = "Estructura modularizada con separación limpia entre unidades de compilación y cabeceras .h."
    elif cant_h >= 1 and not tiene_main:
        tipo = TipoEntrega.LIBRERIA_TDA
        diag = "Diseño de biblioteca / Tipo de Dato Abstracto sin función main() ejecutable directa."
    elif cant_c >= 1 and not tiene_main:
        tipo = TipoEntrega.INCOMPLETA
        diag = "Fuentes C presentes pero sin punto de entrada main() ni interfaz de biblioteca clara."
    else:
        tipo = TipoEntrega.MODULAR
        diag = "Estructura multi-archivo con múltiples fuentes."

    return TipologiaReport(
        estudiante_o_dir=dir_path.name,
        tipologia=tipo,
        cant_c=cant_c,
        cant_h=cant_h,
        total_loc=total_loc,
        tiene_main=tiene_main,
        tiene_makefile=tiene_makefile,
        archivos_c=[str(f.relative_to(dir_path)) for f in archivos_c],
        archivos_h=[str(f.relative_to(dir_path)) for f in archivos_h],
        diagnostico=diag,
    )
