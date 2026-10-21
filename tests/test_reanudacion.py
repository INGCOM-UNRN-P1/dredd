"""Cursor de las corridas masivas en auditoria.json: `dredd eval --resume` y `--failed-only` (Ola 8)."""

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

import dredd.cli.evaluacion as evaluacion
from dredd.cli import app
from dredd.core import auditoria

runner = CliRunner()


@pytest.fixture
def curso(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    entregas = tmp_path / "entrega_3"
    for alumno, codigo in (("alumno1", "int main(void) { return 0; }\n"),
                           ("alumno2", "int main(void) { syntax error here }\n")):
        (entregas / alumno).mkdir(parents=True)
        (entregas / alumno / "main.c").write_text(codigo)
    return entregas


@pytest.fixture
def analizados(monkeypatch):
    """Los directorios que llegaron a analizarse con ripley en cada corrida."""
    vistos: list = []
    original = evaluacion.run_ripley_analysis

    def contar(r_path, *args, **kwargs):
        vistos.append(Path(r_path).parent.name if Path(r_path).name.startswith("r") else Path(r_path).name)
        return original(r_path, *args, **kwargs)

    monkeypatch.setattr(evaluacion, "run_ripley_analysis", contar)
    return vistos


def test_registra_estado_y_resultado(curso, analizados):
    assert runner.invoke(app, ["eval", "entrega_3", "--all"]).exit_code == 0
    bien = auditoria.leer(curso / "alumno1" / "r1i")
    mal = auditoria.leer(curso / "alumno2" / "r1i")
    assert bien["estado"] == mal["estado"] == "completa"
    assert bien["resultado"]["compilacion"] is True
    assert mal["resultado"]["compilacion"] is False
    assert auditoria.fallida(curso / "alumno1" / "r1i") is False
    assert auditoria.fallida(curso / "alumno2" / "r1i") is True


def test_resume_saltea_lo_completo_y_retoma_lo_interrumpido(curso, analizados):
    assert runner.invoke(app, ["eval", "entrega_3", "--all"]).exit_code == 0
    assert sorted(analizados) == ["alumno1", "alumno2"]
    analizados.clear()

    res = runner.invoke(app, ["eval", "entrega_3", "--all", "--resume"])
    assert res.exit_code == 0, res.output
    assert analizados == []
    assert "ya evaluada" in res.output

    # La corrida se cortó a mitad de alumno2: el informe no llegó a escribirse.
    auditoria.marcar(curso / "alumno2" / "r1i", "en_curso")
    res = runner.invoke(app, ["eval", "entrega_3", "--all", "--resume", "--json"])
    assert res.exit_code == 0, res.output
    assert analizados == ["alumno2"]
    datos = json.loads(res.stdout[res.stdout.index("{"):])
    assert datos["resumed"] == 1
    assert auditoria.leer(curso / "alumno2" / "r1i")["estado"] == "completa"


def test_failed_only_evalua_solo_las_que_fallaron(curso, analizados):
    assert runner.invoke(app, ["eval", "entrega_3", "--all"]).exit_code == 0
    analizados.clear()
    res = runner.invoke(app, ["eval", "entrega_3", "--all", "--failed-only"])
    assert res.exit_code == 0, res.output
    assert analizados == ["alumno2"]

    res = runner.invoke(app, ["eval", "entrega_3", "alumno1", "--failed-only"])
    assert res.exit_code == 0 and "Nada para re-evaluar" in res.output
    assert analizados == ["alumno2"]


def test_un_error_queda_en_el_cursor(curso, monkeypatch):
    def falla(*args, **kwargs):
        raise RuntimeError("ripley se cayó")

    monkeypatch.setattr(evaluacion, "run_ripley_analysis", falla)
    assert runner.invoke(app, ["eval", "entrega_3", "alumno1"]).exit_code == 0
    registro = auditoria.leer(curso / "alumno1" / "r1i")
    assert registro["estado"] == "error" and "ripley se cayó" in registro["error"]
    assert auditoria.fallida(curso / "alumno1" / "r1i") is True
    assert not auditoria.completa(curso / "alumno1" / "r1i")


def test_registros_anteriores_al_cursor(tmp_path):
    (tmp_path / "r1i").mkdir()
    (tmp_path / "r1i" / "auditoria.json").write_text(json.dumps({"schema_version": "1.0.0", "versiones": {}}))
    assert auditoria.fallida(tmp_path / "r1i") is None
    assert not auditoria.completa(tmp_path / "r1i")
    assert auditoria.ultima_revision(tmp_path) == tmp_path / "r1i"


def test_completa_compara_el_commit(tmp_path):
    auditoria.registrar(tmp_path, "ana", "tp1", "abc1234", commit="abc1234ffff", estado="completa")
    assert auditoria.completa(tmp_path, commit="abc1234ffff")
    assert not auditoria.completa(tmp_path, commit="0000000")
    assert auditoria.completa(tmp_path)
