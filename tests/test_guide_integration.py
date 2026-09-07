"""Unit tests for Dredd guide integration and deckard connectivity."""

from pathlib import Path
from typer.testing import CliRunner
import yaml

from dredd.cli import app
from dredd.core.guide_integration import (
    ActivityGuide,
    GuideExercise,
    load_activity_guide,
)
from dredd.core.mapping import heuristic_match, InteractiveMapper

runner = CliRunner()


def test_load_activity_guide_from_guia_folder(tmp_path: Path):
    entregas = tmp_path / "entrega-3_1238305"
    entregas.mkdir()
    guia_dir = entregas / "guia"
    guia_dir.mkdir()

    guia_yaml = guia_dir / "guia.yaml"
    guia_yaml.write_text(
        yaml.safe_dump({
            "nombre": "Guía 3 — Arreglos y Punteros",
            "minutos_totales": 45,
            "ejercicios": [
                {
                    "id": "contar-pares",
                    "titulo": "Contar Números Pares",
                    "tema": "arreglos",
                    "bloom": 2,
                    "starter_code": "int contar_pares(const int *v, size_t n);",
                },
                {
                    "id": "invertir-vector",
                    "titulo": "Inversión in-place de Vector",
                    "tema": "punteros",
                    "bloom": 3,
                    "starter_code": "void invertir_vector(int *v, size_t n);",
                },
            ],
        }),
        encoding="utf-8",
    )

    guide = load_activity_guide(entregas, "entrega-3_1238305", tmp_path)
    assert guide is not None
    assert guide.nombre == "Guía 3 — Arreglos y Punteros"
    assert len(guide.exercises) == 2
    assert guide.get_exercise_ids() == ["contar-pares", "invertir-vector"]

    ex1 = guide.get_exercise("contar-pares")
    assert ex1 is not None
    assert "contar_pares" in ex1.functions


def test_heuristic_match_with_guide_functions_and_titles():
    guide = ActivityGuide(
        nombre="Guía Arreglos",
        guide_dir=Path("/tmp"),
        exercises=[
            GuideExercise(
                id="contar-pares",
                titulo="Contar Números Pares",
                functions=["contar_pares"],
            ),
            GuideExercise(
                id="invertir-vector",
                titulo="Invertir Vector",
                functions=["invertir_vector"],
            ),
        ],
    )

    avail = ["contar-pares", "invertir-vector"]

    # 1. Por ID directo o variantes con guion bajo
    assert heuristic_match("contar_pares.c", avail, guide=guide) == "contar-pares"

    # 2. Por coincidencia en título
    assert heuristic_match("inversion.c", avail, guide=guide) == "invertir-vector"

    # 3. Por posición ordinal (ej1 -> contar-pares, ej2 -> invertir-vector)
    assert heuristic_match("ej1.c", avail, guide=guide) == "contar-pares"
    assert heuristic_match("ej2.c", avail, guide=guide) == "invertir-vector"

    # 4. Por análisis del contenido de funciones en el código C
    c_source = "int contar_pares(const int *v, size_t n) { return 0; }\n"
    assert heuristic_match("tarea_alumno.c", avail, file_content=c_source, guide=guide) == "contar-pares"


def test_cli_map_with_guia_folder(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    entregas = tmp_path / "entrega-3_1238305"
    entregas.mkdir()

    # Subdirectorio guia
    guia_dir = entregas / "guia"
    guia_dir.mkdir()
    (guia_dir / "guia.yaml").write_text(
        yaml.safe_dump({
            "nombre": "Guía 3",
            "ejercicios": [
                {"id": "ej-pares", "titulo": "Pares"},
                {"id": "ej-invertir", "titulo": "Invertir"},
            ],
        }),
        encoding="utf-8",
    )

    # Entregas de estudiantes
    est1 = entregas / "perez_juan"
    est1.mkdir()
    (est1 / "ej1.c").write_text("int main() { return 0; }\n")

    # Mapeo automático
    res = runner.invoke(app, ["map", "entrega-3_1238305/", "--auto"])
    assert res.exit_code == 0
    assert "Guía Deckard conectada" in res.output
    assert "ej-pares" in res.output
    assert "ej-invertir" in res.output
    assert "1 mapeo(s) actualizados" in res.output


def test_cli_eval_with_guia_folder_excludes_guia_and_reports_specs(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    entregas = tmp_path / "entrega-3_1238305"
    entregas.mkdir()

    # Subdirectorio guia
    guia_dir = entregas / "guia"
    guia_dir.mkdir()
    (guia_dir / "guia.yaml").write_text(
        yaml.safe_dump({
            "nombre": "Guía Estructuras",
            "ejercicios": [
                {"id": "ej-listas", "titulo": "Listas Enlazadas"},
            ],
        }),
        encoding="utf-8",
    )

    # Alumno
    est1 = entregas / "gomez_maria"
    est1.mkdir()
    (est1 / "main.c").write_text("int main(void) { return 0; }\n")

    res = runner.invoke(app, ["eval", "entrega-3_1238305/", "--all"])
    assert res.exit_code == 0
    # No debe evaluar 'guia' como si fuera un estudiante
    assert "Procesando estudiante: guia" not in res.output
    assert "Procesando estudiante: gomez_maria" in res.output

    rep = est1 / "gomez_maria_r1.md"
    assert rep.is_file()
    rep_text = rep.read_text(encoding="utf-8")
    assert "**Guía vinculada:** `Guía Estructuras`" in rep_text
    assert "`ej-listas (Listas Enlazadas)`" in rep_text


def test_load_guide_from_deckard_dir_with_ripkg(tmp_path: Path):
    import io
    import zipfile
    from dredd.core.guide_integration import load_guide_from_deckard_dir

    deckard_dir = tmp_path / ".deckard"
    deckard_dir.mkdir()
    (deckard_dir / "guia.yaml").write_text(
        yaml.safe_dump({
            "nombre": "Práctica de Prueba",
            "ejercicios": [{"id": "sumador", "titulo": "Sumador de Enteros"}],
        }),
        encoding="utf-8",
    )
    (deckard_dir / "enunciado.md").write_text("# Enunciado General\nConsigna del trabajo.\n", encoding="utf-8")

    # Crear paquete .ripkg falso
    ejs_dir = deckard_dir / "ejercicios"
    ejs_dir.mkdir()
    ripkg_path = ejs_dir / "sumador.ripkg"
    with zipfile.ZipFile(ripkg_path, "w") as z:
        z.writestr("manifest.toml", 'tipo_entrega = "proyecto"\n')
        z.writestr("payload/enunciado.md", "Implementar int sumar(int a, int b);\n")
        z.writestr("payload/pistas.txt", "Usar el operador +\nCuidar overflow\n")
        z.writestr("payload/sumador.h", "int sumar(int a, int b);\n")
        z.writestr("payload/01_basico.in", "2 3\n")
        z.writestr("payload/01_basico.out", "5\n")

    guide = load_guide_from_deckard_dir(deckard_dir)
    assert guide is not None
    assert guide.nombre == "Práctica de Prueba"
    assert guide.enunciado == "# Enunciado General\nConsigna del trabajo."
    assert ".deckard" in guide.enunciado_source

    ex = guide.get_exercise("sumador")
    assert ex is not None
    assert ex.enunciado == "Implementar int sumar(int a, int b);"
    assert ex.pistas == ["Usar el operador +", "Cuidar overflow"]
    assert "sumar" in ex.functions
    assert len(ex.test_cases) == 1
    assert ex.test_cases[0]["nombre"] == "01_basico"
    assert ex.test_cases[0]["entrada"] == "2 3\n"
    assert ex.test_cases[0]["salida"] == "5\n"


def test_deckard_priority_over_general_config(tmp_path: Path):
    """Verifica que si .deckard está presente en la entrega, tiene prioridad sobre dredd.yaml / general."""
    ws = tmp_path / "workspace"
    ws.mkdir()
    (ws / "dredd.yaml").write_text(
        yaml.safe_dump({
            "workspace": {"name": "Test WS"},
            "mapeos": [
                {
                    "zip_pattern": "*",
                    "entrega": "tp1",
                    "guia": "guias_general/guia.yaml",
                    "titulo": "Guía General dredd.yaml",
                }
            ],
        }),
        encoding="utf-8",
    )
    gen_dir = ws / "guias_general"
    gen_dir.mkdir()
    (gen_dir / "guia.yaml").write_text(
        yaml.safe_dump({
            "nombre": "Guía General desde dredd.yaml",
            "ejercicios": [{"id": "ej_general"}],
        }),
        encoding="utf-8",
    )

    # Directorio de entrega con .deckard local
    submission = tmp_path / "entrega_alumno"
    submission.mkdir()
    local_deckard = submission / ".deckard"
    local_deckard.mkdir()
    (local_deckard / "guia.yaml").write_text(
        yaml.safe_dump({
            "nombre": "Guía Específica Local .deckard",
            "ejercicios": [{"id": "ej_local_deckard"}],
        }),
        encoding="utf-8",
    )

    guide = load_activity_guide(submission, "tp1", ws)
    assert guide is not None
    # Debe haber ganado .deckard sobre la configuración general de dredd.yaml
    assert guide.nombre == "Guía Específica Local .deckard"
    assert guide.get_exercise_ids() == ["ej_local_deckard"]
    assert ".deckard" in guide.enunciado_source


def test_fallback_to_general_config_when_deckard_absent(tmp_path: Path):
    """Verifica que si .deckard no está en la entrega, utiliza la configuración general."""
    ws = tmp_path / "workspace"
    ws.mkdir()
    (ws / "dredd.yaml").write_text(
        yaml.safe_dump({
            "workspace": {"name": "Test WS", "practicas_dir": "practicas_catedra"},
            "mapeos": [
                {
                    "zip_pattern": "*",
                    "entrega": "tp1",
                    "guia": "practicas_catedra/tp1",
                    "titulo": "TP1 Cátedra",
                }
            ],
        }),
        encoding="utf-8",
    )
    p_dir = ws / "practicas_catedra" / "tp1"
    p_dir.mkdir(parents=True)
    (p_dir / "guia.yaml").write_text(
        yaml.safe_dump({
            "nombre": "Práctica Oficial Cátedra",
            "ejercicios": [{"id": "oficial_1"}],
        }),
        encoding="utf-8",
    )
    (p_dir / "enunciado.md").write_text("# Consigna Oficial\n", encoding="utf-8")

    submission_vacia = tmp_path / "entrega_sin_deckard"
    submission_vacia.mkdir()

    guide = load_activity_guide(submission_vacia, "tp1", ws)
    assert guide is not None
    assert guide.nombre == "Práctica Oficial Cátedra"
    assert guide.get_exercise_ids() == ["oficial_1"]
    assert "configuración general" in guide.enunciado_source
    assert guide.enunciado == "# Consigna Oficial"


def test_reporter_writes_enunciado_markdown(tmp_path: Path):
    from dredd.core.guide_integration import ActivityGuide, GuideExercise
    from dredd.core.reporter import write_individual_tool_reports

    guide = ActivityGuide(
        nombre="Trabajo Práctico 1",
        guide_dir=tmp_path,
        enunciado="# Consigna Global del TP1",
        enunciado_source=".deckard (/tmp/test/.deckard)",
        exercises=[
            GuideExercise(
                id="ej1",
                titulo="Ejercicio 1",
                enunciado="Desarrollar la función f(x)",
                pistas=["Revisar caso x=0"],
            )
        ],
    )
    rni = tmp_path / "r1_f"
    generated = write_individual_tool_reports(rni, {}, guide=guide)
    assert "enunciado" in generated
    assert (rni / "enunciado.md").is_file()
    content = (rni / "enunciado.md").read_text(encoding="utf-8")
    assert "## 📋 Consigna y Enunciado — Trabajo Práctico 1" in content
    assert "# Consigna Global del TP1" in content
    assert "Desarrollar la función f(x)" in content
    assert "Revisar caso x=0" in content
