"""Tests para el comparador de versiones sucesivas de entregas (QoL 3.15)."""

import json
from pathlib import Path
from typer.testing import CliRunner

from dredd.cli import app
from dredd.core.diff_submission import (
    comparar_revisiones_entrega,
    generar_markdown_diff_submission,
    resolver_carpetas_revision,
)

runner = CliRunner()


def test_comparar_revisiones_entrega_basico(tmp_path):
    dir_r1 = tmp_path / "alumno1" / "r1"
    dir_r2 = tmp_path / "alumno1" / "r2"
    dir_r1.mkdir(parents=True)
    dir_r2.mkdir(parents=True)

    (dir_r1 / "main.c").write_text("int main(void) {\n    return 0;\n}\n")
    (dir_r2 / "main.c").write_text("int main(void) {\n    int x = 10;\n    return x;\n}\n")

    (dir_r1 / "eliminado.c").write_text("void vieja(void) {}\n")
    (dir_r2 / "nuevo.c").write_text("void nueva(void) {}\n")

    diff = comparar_revisiones_entrega(dir_r1, dir_r2, "r1", "r2")
    assert diff.archivos_modificados == 1
    assert diff.archivos_nuevos == 1
    assert diff.archivos_eliminados == 1
    assert diff.total_agregadas >= 2
    assert diff.total_eliminadas >= 1

    md = generar_markdown_diff_submission(diff)
    assert "main.c" in md
    assert "nuevo.c" in md
    assert "eliminado.c" in md
    assert "MODIFICADO" in md


def test_cli_diff_submission_directorios(tmp_path):
    dir_r1 = tmp_path / "v1"
    dir_r2 = tmp_path / "v2"
    dir_r1.mkdir()
    dir_r2.mkdir()

    (dir_r1 / "lista.c").write_text("void insertar(void) {}\n")
    (dir_r2 / "lista.c").write_text("void insertar(void) {}\nvoid eliminar(void) {}\n")

    out_md = tmp_path / "diff.md"
    res = runner.invoke(app, ["diff-submission", str(dir_r1), str(dir_r2), "--md", str(out_md)])
    assert res.exit_code == 0
    assert out_md.exists()
    assert "insertar" in out_md.read_text(encoding="utf-8")

    # Prueba con salida JSON
    res_json = runner.invoke(app, ["diff-submission", str(dir_r1), str(dir_r2), "--json"])
    assert res_json.exit_code == 0
    data = json.loads(res_json.stdout)
    assert data["archivos_modificados"] == 1
    assert data["total_agregadas"] >= 1
