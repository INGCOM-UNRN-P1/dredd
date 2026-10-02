"""Caracterización de `run_ripley_analysis` (N-ECO-16).

golden_run_ripley_analysis.json se generó antes de partir la función de 514 líneas: si este test falla,
el refactor cambió el resultado o qué colaboradores se llaman, con qué argumentos o en qué orden. Ver
tests/caracterizacion/run_ripley_analysis.py.
"""

import importlib.util
import json
from pathlib import Path

import pytest

_RUTA = Path(__file__).parent / "caracterizacion" / "run_ripley_analysis.py"
_spec = importlib.util.spec_from_file_location("caracterizacion_run_ripley_analysis", _RUTA)
_escenarios = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_escenarios)

GOLDEN = json.loads(_escenarios.GOLDEN.read_text(encoding="utf-8"))


def test_el_golden_cubre_todos_los_escenarios():
    assert set(GOLDEN) == set(_escenarios.ESCENARIOS)


@pytest.mark.parametrize("escenario", sorted(GOLDEN))
def test_mismo_resultado_y_mismas_llamadas_que_antes_del_refactor(escenario):
    obtenido = json.loads(json.dumps(_escenarios.ejecutar(escenario), ensure_ascii=False, default=str))
    assert obtenido == GOLDEN[escenario]
