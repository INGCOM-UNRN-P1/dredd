from pathlib import Path
from typer.testing import CliRunner
import yaml

from dredd.cli import app
from dredd.core.config import MappingRule, DreddConfig, WorkspaceSettings, ToolChecksConfig, load_dredd_config

runner = CliRunner()


def test_mapping_rule_github(tmp_path: Path):
    rule = MappingRule(
        zip_pattern="*",
        entrega="tp04",
        source="github",
        github_org="Catedra-UNRN",
        repo_pattern="tp04-*",
        branch="dev",
    )
    assert rule.matches_github_repo("tp04-estudiante1") is True
    assert rule.matches_github_repo("tp05-estudiante1") is False

    cfg = DreddConfig(
        workspace=WorkspaceSettings(default_source="github"),
        checks=ToolChecksConfig(),
        mapeos=[rule],
        config_path=tmp_path / "dredd.yaml",
    )
    saved_path = cfg.save()
    assert saved_path.is_file()

    loaded = load_dredd_config(tmp_path)
    assert loaded is not None
    assert loaded.workspace.default_source == "github"
    assert len(loaded.mapeos) == 1
    assert loaded.mapeos[0].source == "github"
    assert loaded.mapeos[0].repo_pattern == "tp04-*"
    assert loaded.mapeos[0].branch == "dev"


def test_cli_config_add_entrega_github(tmp_path: Path):
    dredd_yaml = tmp_path / "dredd.yaml"
    dredd_yaml.write_text("""version: '1.0'
workspace:
  name: Cátedra Programación 1
checks: {}
mapeos: []
""", encoding="utf-8")

    res = runner.invoke(app, [
        "config", "add-entrega", "tp05",
        "--source", "github",
        "--github-org", "OrgTest",
        "--repo-pattern", "tp05-alumno-*",
        "--branch", "main",
        "--workspace", str(tmp_path),
    ])
    assert res.exit_code == 0
    assert "ORIGEN: GITHUB" in res.stdout.upper() or "GITHUB" in res.stdout

    # Verificar que se persistió en YAML
    raw = yaml.safe_load(dredd_yaml.read_text(encoding="utf-8"))
    assert raw["mapeos"][0]["source"] == "github"
    assert raw["mapeos"][0]["github_org"] == "OrgTest"
    assert raw["mapeos"][0]["repo_pattern"] == "tp05-alumno-*"

    # Probar config show
    res_show = runner.invoke(app, ["config", "show", "--workspace", str(tmp_path)])
    assert res_show.exit_code == 0
    assert "GitHub" in res_show.stdout
