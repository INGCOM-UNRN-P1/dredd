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


def test_map_de_una_actividad_sin_entregas_es_un_error(tmp_path, monkeypatch):
    """`dredd map no_existe` respondía «No se encontraron archivos .c para mapear» con código 0."""
    monkeypatch.chdir(tmp_path)
    res = runner.invoke(app, ["map", "no_existe"], env={"COLUMNS": "200"})
    assert res.exit_code == 2, res.output
    assert "no_existe" in res.output


def test_eval_shielded_propaga_el_codigo_de_salida(monkeypatch):
    """Mostraba «Código de salida: -1» (no se pudo ejecutar) y terminaba con 0."""
    import dredd.core.sandbox as sandbox

    for retorno, esperado in (((-1, "", "no existe", False), 1), ((3, "", "", False), 3),
                              ((0, "ok", "", False), 0), ((0, "", "", True), 1)):
        monkeypatch.setattr(sandbox, "execute_shielded_sandbox", lambda *a, _r=retorno, **k: _r)
        res = runner.invoke(app, ["eval-shielded", "./programa"])
        assert res.exit_code == esperado, (retorno, res.output)
