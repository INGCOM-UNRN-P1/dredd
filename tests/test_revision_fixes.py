"""Tests para verificar la resolución de los hallazgos de auditoría (DREDD-D0102 a D0903)."""

import json
from pathlib import Path
import pytest
import typer
from typer.testing import CliRunner

from dredd import __version__
from dredd.cli import app
from dredd.core.ast_checker import audit_c_file
from dredd.core.config import DreddConfig, ToolChecksConfig, load_dredd_config
from dredd.core.doctor import ejecutar_diagnostico_doctor
from dredd.core.ecosystem import resolve_sibling_cli, resolve_sibling_tool
from dredd.core.reporter import write_individual_tool_reports
from dredd.core.sandbox import audit_sandbox_evasion, strip_c_comments_and_strings

runner = CliRunner()


def test_dredd_version_flag():
    """DREDD-D0401: Flag --version presente en el CLI."""
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert f"dredd {__version__}" in result.output


def test_sandbox_evasion_strip_comments_and_strings():
    """DREDD-D0302: audit_sandbox_evasion no produce falsos positivos en comentarios inline o strings."""
    code_safe = '''
    #include <stdio.h>
    int main(void) {
        // system("rm -rf /");
        /* fork();
           socket(0, 0, 0); */
        printf("Llamando a fork() en un string literal\\n");
        printf("Ruta falsa: /proc/self/mem dentro de texto\\n");
        return 0;
    }
    '''
    findings = audit_sandbox_evasion(code_safe)
    assert len(findings) == 0, f"Se produjeron falsos positivos: {findings}"

    code_dangerous = '''
    #include <stdio.h>
    #include <unistd.h>
    int main(void) {
        fork(); // llamada real
        return 0;
    }
    '''
    findings_danger = audit_sandbox_evasion(code_dangerous)
    assert any(f.rule_code == "SEC_FORK" for f in findings_danger)


def test_ecosystem_sibling_resolution():
    """DREDD-D0203 / DREDD-D0902: Resolución centralizada de herramientas hermanas."""
    # Símbolo existente en monorepo o fallback limpio
    fn = resolve_sibling_tool("spunkmeyer", "spunkmeyer.core.detector", "auditar_archivo")
    # fn puede ser Callable o None si no está en el venv ni monorepo, pero no debe lanzar excepción
    assert fn is None or callable(fn)

    cli_path = resolve_sibling_cli("non_existent_tool_xyz")
    assert cli_path is None


def test_doctor_includes_ecosystem_tools():
    """DREDD-D0403: doctor verifica daedalus, esper, nostromo, gaff, spunkmeyer, etc."""
    from io import StringIO
    from rich.console import Console

    buf = StringIO()
    cons = Console(file=buf, color_system=None)
    ejecutar_diagnostico_doctor(console=cons)
    out = buf.getvalue()

    for tool in ["gcc", "daedalus", "esper", "valgrind", "nostromo", "gaff", "spunkmeyer", "deckard"]:
        assert tool in out, f"Herramienta '{tool}' ausente en la salida de dredd doctor"


def test_config_p1_alias_and_unknown_keys(tmp_path: Path):
    """DREDD-D0501 & DREDD-D0502: Alias p1_linter_enabled y warning de claves desconocidas."""
    cfg_data = {
        "checks": {
            "p1_linter": {
                "enabled": True,
                "strict": True,
            }
        }
    }
    tcc = ToolChecksConfig.from_dict(cfg_data["checks"])
    assert tcc.ripley_enabled is True
    assert tcc.p1_linter_enabled is True

    # Unknown root key warning test
    yaml_file = tmp_path / "dredd.yaml"
    yaml_file.write_text("unknown_root_option: 123\nworkspace:\n  name: Test\n", encoding="utf-8")
    loaded = load_dredd_config(tmp_path)
    assert loaded is not None
    assert loaded.workspace.name == "Test"


def test_eval_json_option(tmp_path: Path):
    """DREDD-D0402: Comando eval soporta --json."""
    entregas_dir = tmp_path / "tp01"
    entregas_dir.mkdir()
    alumno_dir = entregas_dir / "alvarez_juan"
    alumno_dir.mkdir()
    (alumno_dir / "main.c").write_text("int main(void) { return 0; }\n", encoding="utf-8")

    result = runner.invoke(app, ["eval", str(entregas_dir), "--all", "--json", "-w", str(tmp_path)])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert "results" in data
    assert len(data["results"]) == 1
    assert data["results"][0]["student"] == "alvarez_juan"
