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


def test_deckard_sync_empaqueta_lo_que_esta_en_el_banco(tmp_path: Path, monkeypatch):
    import subprocess

    from typer.testing import CliRunner

    from dredd.cli import app

    for eid in ("a", "b"):
        (tmp_path / "banco" / eid).mkdir(parents=True)
        (tmp_path / "banco" / eid / "ejercicio.yaml").write_text(f"id: {eid}\n", encoding="utf-8")
    (tmp_path / "ws").mkdir()
    ws = _workspace(tmp_path / "ws", "  deckard_bank_dir: ../banco\nmapeos:\n- entrega: e9\n  guia: guias/e9/guia.yaml\n")
    (ws / "guias" / "e9").mkdir(parents=True)
    (ws / "guias" / "e9" / "guia.yaml").write_text("ejercicios:\n- id: a\n- id: b\n- id: z\n", encoding="utf-8")
    (ws / "guias" / "e9" / "b.ripkg").write_bytes(b"previo")

    llamadas = []

    def falso_pack(cmd, **_):
        if "--help" in cmd:
            return subprocess.CompletedProcess(cmd, 0, "Uso: deckard export pack [OPCIONES] {objetivo}", "")
        llamadas.append(cmd[3])
        Path(cmd[cmd.index("--salida") + 1]).write_bytes(b"PK")
        return subprocess.CompletedProcess(cmd, 0, "", "")

    monkeypatch.setattr("shutil.which", lambda _: "/usr/bin/deckard")
    monkeypatch.setattr(subprocess, "run", falso_pack)
    monkeypatch.chdir(ws)
    res = CliRunner().invoke(app, ["deckard", "sync", "e9"])
    assert res.exit_code == 0, res.output
    assert llamadas == ["a"]
    assert (ws / "guias" / "e9" / "b.ripkg").read_bytes() == b"previo"
    assert "No están en el banco" in res.output and "z" in res.output


def test_deckard_sync_con_deckard_viejo_falla_una_vez(tmp_path: Path, monkeypatch):
    import subprocess

    from typer.testing import CliRunner

    from dredd.cli import app

    (tmp_path / "banco" / "a").mkdir(parents=True)
    (tmp_path / "banco" / "a" / "ejercicio.yaml").write_text("id: a\n", encoding="utf-8")
    (tmp_path / "ws").mkdir()
    ws = _workspace(tmp_path / "ws", "  deckard_bank_dir: ../banco\nmapeos:\n- entrega: e9\n  guia: guias/e9/guia.yaml\n")
    (ws / "guias" / "e9").mkdir(parents=True)
    (ws / "guias" / "e9" / "guia.yaml").write_text("ejercicios:\n- id: a\n", encoding="utf-8")
    monkeypatch.setattr("shutil.which", lambda _: "/usr/bin/deckard")
    monkeypatch.setattr(subprocess, "run", lambda cmd, **_: subprocess.CompletedProcess(cmd, 0, "Uso: deckard export run", ""))
    monkeypatch.chdir(ws)
    res = CliRunner().invoke(app, ["deckard", "sync", "e9"])
    assert res.exit_code == 1
    assert not (ws / "guias" / "e9" / "a.ripkg").exists()


def test_actividad_duplicada_en_la_raiz_usa_la_de_submissions_dir(tmp_path: Path, monkeypatch, capsys):
    """F-06: con entregas/entrega_1 y ./entrega_1, el nombre resuelve a la declarada (donde escribe la ingesta)."""
    from dredd.core.git_ops import resolve_submissions_dir

    ws = _workspace(tmp_path, "mapeos:\n- zip_pattern: '*Entrega #1-1228009.zip'\n  entrega: entrega_1\n")
    (ws / "entregas" / "entrega_1").mkdir(parents=True)
    (ws / "entrega_1").mkdir()
    monkeypatch.chdir(ws)
    assert resolve_submissions_dir(ws, "entrega_1") == ("entrega_1", (ws / "entregas" / "entrega_1").resolve())
    assert "también en" in capsys.readouterr().err
    # una ruta explícita sigue mandando
    assert resolve_submissions_dir(ws, "./entrega_1")[1] == (ws / "entrega_1").resolve()


def test_regla_de_github_no_se_queda_con_cualquier_zip(tmp_path: Path):
    """Una regla sin zip_pattern (GitHub) no coincide con ZIPs ni nombres ajenos (antes valía «*»)."""
    from dredd.core.git_ops import resolve_submissions_dir

    ws = _workspace(tmp_path, "mapeos:\n- entrega: TP0\n  source: github\n- zip_pattern: '*Entrega #1-*.zip'\n  entrega: entrega_1\n")
    (ws / "entregas" / "TP0").mkdir(parents=True)
    (ws / "entregas" / "parcial_1").mkdir(parents=True)
    cfg = load_dredd_config(ws)
    assert cfg.find_mapping_for_zip("PROG1 Parcial 1-1250000.zip") is None
    assert cfg.find_mapping_for_zip("PROG1 Entrega #1-1228009.zip").entrega == "entrega_1"
    assert resolve_submissions_dir(ws, "parcial_1")[1] == (ws / "entregas" / "parcial_1").resolve()
    import yaml

    assert "zip_pattern" not in yaml.safe_load(cfg.to_yaml())["mapeos"][0]


def test_estilo_usa_el_cli_de_gaff_con_rutas_relativas(tmp_path: Path, monkeypatch):
    """La sección Gaff sale del mismo `gaff` que hace `gaff fix`, sin las bibliotecas de la cátedra."""
    import json
    import subprocess

    from dredd.core import ripley_client

    for rel in ("ejercicios/ej1/main.c", "ejercicios/ej2/main.c", "libs/p1_test/src/p1_test.c"):
        (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / rel).write_text("int main(void)\n{\n    return 0;\n}\n", encoding="utf-8")
    salida = {"archivos": [
        {"archivo": a, "violaciones": [{"codigo": "0x0101h", "titulo": "Nombres", "archivo": a, "linea": 3,
                                        "columna": 5, "mensaje": "corto", "es_autofixable": False}]}
        for a in ("ejercicios/ej1/main.c", "ejercicios/ej2/main.c", "libs/p1_test/src/p1_test.c")]}
    llamadas = []

    def falso_run(cmd, **kwargs):
        llamadas.append((cmd, kwargs.get("cwd")))
        return subprocess.CompletedProcess(cmd, 1, json.dumps(salida), "")

    monkeypatch.setattr(ripley_client, "resolve_sibling_cli", lambda nombre: "/usr/bin/gaff")
    monkeypatch.setattr(ripley_client.subprocess, "run", falso_run)
    hallazgos, _ = ripley_client.audit_style_with_gaff(tmp_path)
    assert [h["file"] for h in hallazgos] == ["ejercicios/ej1/main.c", "ejercicios/ej2/main.c"]
    assert llamadas == [(["/usr/bin/gaff", "check", "-r", ".", "--json"], str(tmp_path))]


def test_hallazgos_de_ripley_sin_la_biblioteca_de_la_catedra(tmp_path: Path, monkeypatch):
    import json
    import subprocess

    from dredd.core import ripley_client
    from dredd.core.config import ToolChecksConfig

    salida = {"hallazgos": [
        {"codigo": "0x7001h", "mensaje": "m", "archivo": "ejercicios/ej1/main.c", "linea": 3, "herramienta": "antipatterns"},
        {"codigo": "0x7001h", "mensaje": "m", "archivo": "libs/p1_test/include/p1_arrays.h", "linea": 9,
         "herramienta": "antipatterns"},
    ]}
    monkeypatch.setattr(ripley_client, "resolve_sibling_cli", lambda nombre: "/usr/bin/ripley")
    monkeypatch.setattr(ripley_client.subprocess, "run",
                        lambda cmd, **kw: subprocess.CompletedProcess(cmd, 1, json.dumps(salida), ""))
    checks = ToolChecksConfig.get_strict_preset()
    hallazgos = ripley_client._collect_ast_findings(tmp_path, checks, set())
    assert [h["file"] for h in hallazgos] == ["ejercicios/ej1/main.c"]
