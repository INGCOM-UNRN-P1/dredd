"""Integración dredd ↔ workspace ↔ deckard (revisión, Ola 27): lo que dredd.yaml declara se usa."""

from pathlib import Path

from dredd.cli.evaluacion import resolver_plantillas
from dredd.core.config import DreddConfig, load_dredd_config


def _workspace(tmp_path: Path, extra: str = "") -> Path:
    (tmp_path / "dredd.yaml").write_text(
        "version: '1.0'\nworkspace:\n  submissions_dir: entregas\n  plantillas_dir: plantillas\n" + extra,
        encoding="utf-8",
    )
    return tmp_path


def test_plantillas_por_omision_son_las_de_dredd_yaml(tmp_path: Path):
    ws = _workspace(tmp_path)
    (ws / "plantillas").mkdir()
    (ws / "plantillas" / "header.md").write_text("# Informe · Programación 1\n", encoding="utf-8")
    cfg = load_dredd_config(ws)
    assert cfg is not None
    assert resolver_plantillas(None, ws, cfg) == ws / "plantillas"


def test_plantillas_explicitas_ganan(tmp_path: Path):
    ws = _workspace(tmp_path)
    (ws / "plantillas").mkdir()
    cfg = load_dredd_config(ws)
    assert resolver_plantillas(Path("otra"), ws, cfg) == Path("otra")


def test_plantillas_sin_directorio_declarado_usan_informe(tmp_path: Path):
    assert resolver_plantillas(None, tmp_path, DreddConfig()) == tmp_path / "informe"


def test_plagio_usa_el_umbral_de_dredd_yaml(tmp_path: Path, monkeypatch):
    """F-04: sin --threshold vale checks.plagiarism.threshold; con strip_boilerplate: false no se quita _baseline."""
    from typer.testing import CliRunner

    from dredd.cli import app
    from dredd.core import plagiarism

    ws = _workspace(tmp_path, "checks:\n  plagiarism:\n    threshold: 0.55\n    strip_boilerplate: false\n")
    (ws / "entregas" / "TP0" / "a").mkdir(parents=True)
    llamadas = []
    original = plagiarism.PlagiarismDetector.analyze_submissions

    def espiar(self, submissions_dir, threshold=None, plantilla=None, buscar_plantilla=True):
        llamadas.append((self.threshold, buscar_plantilla))
        return original(self, submissions_dir, threshold, plantilla, buscar_plantilla)

    monkeypatch.setattr(plagiarism.PlagiarismDetector, "analyze_submissions", espiar)
    monkeypatch.chdir(ws)
    runner = CliRunner()
    res = runner.invoke(app, ["plagiarism", "TP0"])
    assert res.exit_code == 0, res.output
    assert "55%" in res.output
    res = runner.invoke(app, ["plagiarism", "TP0", "--threshold", "0.8"])
    assert res.exit_code == 0, res.output
    assert llamadas == [(0.55, False), (0.8, False)]


def test_fuzz_gen_resuelve_la_solucion_modelo_del_banco(tmp_path: Path, monkeypatch):
    import pytest
    import typer

    from dredd.cli.analisis import resolver_modelo

    (tmp_path / "banco" / "contador-digitos").mkdir(parents=True)
    solucion = tmp_path / "banco" / "contador-digitos" / "solucion.c"
    solucion.write_text("int main(void) { return 0; }\n", encoding="utf-8")
    (tmp_path / "ws").mkdir()
    ws = _workspace(tmp_path / "ws", "  deckard_bank_dir: ../banco\n")
    assert resolver_modelo("contador-digitos", ws).resolve() == solucion.resolve()
    assert resolver_modelo(str(solucion), ws) == solucion
    with pytest.raises(typer.Exit) as exc:
        resolver_modelo("no-existe", ws)
    assert exc.value.exit_code == 2
