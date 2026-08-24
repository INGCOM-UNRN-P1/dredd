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
