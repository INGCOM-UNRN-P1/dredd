"""Pruebas del comando multiplex en dredd CLI."""

from pathlib import Path
import pytest
import yaml
from typer.testing import CliRunner

from dredd.cli import app

runner = CliRunner()


def test_dredd_cli_multiplex(tmp_path):
    matriz_file = tmp_path / "matriz.yaml"
    with open(matriz_file, "w", encoding="utf-8") as f:
        yaml.safe_dump({
            "ejercicio": "dredd_tp_lista",
            "titulo": "Lista Parametrizada",
            "enunciado_template": "Lista de {{ t }}.",
            "parametrizaciones": {"t": ["int", "double"]},
        }, f)

    out_dir = tmp_path / "dist_dredd"
    res = runner.invoke(app, [
        "multiplex",
        "--spec", str(matriz_file),
        "-o", str(out_dir),
    ])

    assert res.exit_code == 0
    assert "✓ Multiplexación completada para 'dredd_tp_lista'" in res.stdout
    assert "Total de variantes combinatorias: 2" in res.stdout
    assert (out_dir / "paquetes" / "dredd_tp_lista_v0.ripkg").is_file()
