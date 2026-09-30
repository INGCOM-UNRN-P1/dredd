"""Una ruta que no existe es un error de uso, no un resultado vacío con código 0 (N-ECO-18)."""

import pytest
from typer.testing import CliRunner

from dredd.cli import app

runner = CliRunner()


@pytest.mark.parametrize("comando", ["typology", "cohort-bench", "audit-git", "export-feedback", "export-guarani"])
def test_una_ruta_que_no_existe_es_un_error_de_uso(comando, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)  # el código anterior escribía, p. ej., acta_guarani.csv en el directorio actual
    res = runner.invoke(app, [comando, "no_existe"], env={"COLUMNS": "200"})
    assert res.exit_code == 2, res.output
    assert "no_existe" in res.output
