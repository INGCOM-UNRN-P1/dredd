"""Caracterización de write_individual_tool_reports (revisión 07: partir la función).

golden_informes.json se generó antes de partirla (tests/caracterizacion/generar_golden_informes.py).
"""

import importlib.util
import json
from pathlib import Path

DIRECTORIO = Path(__file__).parent / "caracterizacion"
_spec = importlib.util.spec_from_file_location("generar_golden_informes", DIRECTORIO / "generar_golden_informes.py")
_generador = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_generador)


def test_mismos_informes_que_antes_del_refactor():
    esperado = json.loads((DIRECTORIO / "golden_informes.json").read_text(encoding="utf-8"))
    assert _generador.golden() == esperado
