"""Contrato de línea de comandos (LINEAMIENTOS §3.2, N-ECO-04): -h/--help, --version/-v y doctor --json."""

from __future__ import annotations

import json

import pytest
from typer.testing import CliRunner

from dredd.cli import app

runner = CliRunner()


@pytest.mark.parametrize("opcion", ["-h", "--help"])
def test_ayuda(opcion):
    resultado = runner.invoke(app, [opcion])
    assert resultado.exit_code == 0, resultado.output


@pytest.mark.parametrize("opcion", ["--version", "-v"])
def test_version(opcion):
    resultado = runner.invoke(app, [opcion])
    assert resultado.exit_code == 0, resultado.output
    assert resultado.output.strip()


def test_doctor_json():
    resultado = runner.invoke(app, ["doctor", "--json"])
    datos = json.loads(resultado.stdout)
    assert "schema_version" in datos
    if "ok" in datos:
        assert resultado.exit_code == (0 if datos["ok"] else 1), resultado.output
