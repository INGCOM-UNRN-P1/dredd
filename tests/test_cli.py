"""Unit tests for Dredd CLI."""

from pathlib import Path
from typer.testing import CliRunner
from dredd.cli import app

runner = CliRunner()


def test_cli_help():
    res = runner.invoke(app, ["--help"])
    assert res.exit_code == 0
    assert "eval" in res.output
    assert "comment" in res.output
    assert "plagiarism" in res.output
    assert "moodle" in res.output


def test_cli_plagiarism_empty(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "tp01-submissions").mkdir()
    res = runner.invoke(app, ["plagiarism", "tp01"])
    assert res.exit_code == 0
    assert "No se detectaron pares con similitud" in res.output


def test_cli_eval_direct_directory(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    entregas = tmp_path / "entrega-3_1238305"
    entregas.mkdir()
    est = entregas / "alumno1"
    est.mkdir()
    (est / "main.c").write_text("int main(void) { return 0; }\n")

    res = runner.invoke(app, ["eval", "entrega-3_1238305/", "--all"])
    assert res.exit_code == 0
    assert "alumno1" in res.output
    # El informe debe quedar en la misma carpeta que la entrega con versión revisada
    reporte_esperado = est / "alumno1_r1.md"
    assert reporte_esperado.is_file()
    assert "Informe de Corrección" in reporte_esperado.read_text(encoding="utf-8")


