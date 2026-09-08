"""Unit tests for Dredd CLI."""

from pathlib import Path
from typer.testing import CliRunner
from dredd.cli import app

runner = CliRunner()


def test_cli_help():
    res = runner.invoke(app, ["--help"])
    assert res.exit_code == 0
    assert "eval" in res.output
    assert "github" in res.output
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
    reporte_esperado = est / "alumno1_r1.md"
    assert reporte_esperado.is_file()
    assert "Informe de Corrección" in reporte_esperado.read_text(encoding="utf-8")


def test_cli_rerun_all_passed(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    entregas = tmp_path / "entrega_3"
    entregas.mkdir()
    est = entregas / "alumno1"
    est.mkdir()
    (est / "main.c").write_text("int main(void) { return 0; }\n")

    # Primero evaluamos para que apruebe
    res1 = runner.invoke(app, ["eval", "entrega_3", "--all"])
    assert res1.exit_code == 0
    assert (est / "alumno1_r1.md").is_file()

    # Rerun con failed-only por defecto: no debería volver a evaluar alumno1
    res2 = runner.invoke(app, ["rerun", "entrega_3"])
    assert res2.exit_code == 0
    assert "están aprobadas y sin fallos" in res2.output or "Nada para re-evaluar" in res2.output


def test_cli_rerun_failed_student(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    entregas = tmp_path / "entrega_3"
    entregas.mkdir()

    # Alumno 1 aprobado
    est1 = entregas / "alumno1"
    est1.mkdir()
    (est1 / "main.c").write_text("int main(void) { return 0; }\n")

    # Alumno 2 fallido (error de sintaxis en C)
    est2 = entregas / "alumno2"
    est2.mkdir()
    (est2 / "main.c").write_text("int main(void) { syntax error here }\n")

    # Primera pasada
    res1 = runner.invoke(app, ["eval", "entrega_3", "--all"])
    assert res1.exit_code == 0
    assert (est1 / "alumno1_r1.md").is_file()
    assert (est2 / "alumno2_r1.md").is_file()

    # Rerun con failed-only: debe seleccionar alumno2 pero ignorar alumno1
    res2 = runner.invoke(app, ["rerun", "entrega_3"])
    assert res2.exit_code == 0
    assert "alumno2" in res2.output
    # alumno1 no debe procesarse de nuevo
    assert "Procesando estudiante: alumno1" not in res2.output


def test_cmd_eval_direct_call_without_args(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    entregas = tmp_path / "entrega_3"
    entregas.mkdir()
    est = entregas / "alumno1"
    est.mkdir()
    (est / "main.c").write_text("int main(void) { return 0; }\n")

    from dredd.cli import cmd_eval
    # Llamada directa desde Python sin pasar opciones de Typer (deben auto-desenvolverse)
    cmd_eval(exercise="entrega_3", student=None, all_students=True)
    assert (est / "alumno1_r1.md").is_file()


def test_get_delivery_mode_safeguard():
    import typer
    from dredd.core.config import DreddConfig
    cfg = DreddConfig()
    opt = typer.Option(None)
    mode = cfg.get_delivery_mode(cli_override=opt)
    assert mode == "archivos_individuales"



