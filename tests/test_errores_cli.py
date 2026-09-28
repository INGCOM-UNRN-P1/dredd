"""Errores de datos y fechas inválidas como mensajes, no como tracebacks (N-ECO-05, N-DREDD-05).

Se invoca la app como lo hace el ejecutable `dredd` (Typer.__call__), que es
donde actúa TyperConErrores; CliRunner la saltea.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from dredd.cli import app

runner = CliRunner()


def test_init_sobre_un_archivo_existente_es_un_mensaje(tmp_path: Path, monkeypatch, capsys):
    (tmp_path / "archivo.c").write_text("int x;\n")
    monkeypatch.chdir(tmp_path)
    with pytest.raises(SystemExit) as salida:
        app(["init", "archivo.c"], prog_name="dredd")
    err = capsys.readouterr().err
    assert salida.value.code == 1
    assert "ya existe" in err
    assert "Traceback" not in err


def test_p1_depurar_deja_ver_la_excepcion(tmp_path: Path, monkeypatch):
    (tmp_path / "archivo.c").write_text("int x;\n")
    monkeypatch.setenv("P1_DEPURAR", "1")
    monkeypatch.chdir(tmp_path)
    with pytest.raises(FileExistsError):
        app(["init", "archivo.c"], prog_name="dredd")


def test_late_penalty_con_fecha_invalida_explica_el_formato():
    resultado = runner.invoke(app, ["late-penalty", "archivo.c", "2026-09-25 23:59"])
    assert resultado.exit_code == 2
    assert "no es una fecha válida" in resultado.output
    assert resultado.exception is None or isinstance(resultado.exception, SystemExit)


def test_late_penalty_acepta_el_formato_con_espacio():
    resultado = runner.invoke(app, ["late-penalty", "2026-09-26 00:30", "2026-09-25 23:59", "--json"])
    assert resultado.exit_code == 0, resultado.output
    assert '"nota_final"' in resultado.output
