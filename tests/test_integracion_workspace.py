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
