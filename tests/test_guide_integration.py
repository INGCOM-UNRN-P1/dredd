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
