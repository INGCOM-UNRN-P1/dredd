"""Unit tests for baseline comparison and exercise filtering in Dredd."""

from pathlib import Path
import pytest

from dredd.core.baseline import (
    classify_submission_exercises,
    find_baseline_dir,
    is_exercise_dir_completed,
    is_file_unmodified_from_baseline,
    resolve_baseline_revision,
    strip_c_comments,
)
from dredd.core.makefile_eval import evaluate_makefile_exercises


def test_strip_c_comments():
    code_with_comments = """
    /* Encabezado del ejercicio */
    // Comentario de una linea
    #include <stdio.h>
    int suma(int a, int b) {
        /* retorna la suma */
        return a + b; // suma directa
    }
    """
    clean = strip_c_comments(code_with_comments)
    assert "/*" not in clean
    assert "*/" not in clean
    assert "//" not in clean
    assert "int suma(int a, int b)" in clean
    assert "return a + b;" in clean


def test_is_file_unmodified_from_baseline(tmp_path: Path):
    template = tmp_path / "base.c"
    template.write_text("/* Plantilla catedra */\nint foo(void);\n", encoding="utf-8")

    # 1. Idéntico
    student_identical = tmp_path / "identical.c"
    student_identical.write_text("/* Plantilla catedra */\nint foo(void);\n", encoding="utf-8")
    assert is_file_unmodified_from_baseline(student_identical, template) is True

    # 2. Solo espacios diferentes
    student_spaces = tmp_path / "spaces.c"
    student_spaces.write_text("  /* Plantilla catedra */\n\nint foo(void);\n  ", encoding="utf-8")
    assert is_file_unmodified_from_baseline(student_spaces, template) is True

    # 3. Solo comentarios modificados (ej: alumno puso su nombre arriba pero no implementó)
    student_comment = tmp_path / "comment.c"
    student_comment.write_text("/* Alumno: Juan Perez */\nint foo(void);\n", encoding="utf-8")
    assert is_file_unmodified_from_baseline(student_comment, template) is True

    # 4. Archivo vacío
    student_empty = tmp_path / "empty.c"
    student_empty.write_text("   \n", encoding="utf-8")
    assert is_file_unmodified_from_baseline(student_empty, template) is True

    # 5. Archivo modificado con código real
    student_code = tmp_path / "code.c"
    student_code.write_text("/* Alumno */\nint foo(void) { return 42; }\n", encoding="utf-8")
    assert is_file_unmodified_from_baseline(student_code, template) is False


def test_find_baseline_dir_hierarchy(tmp_path: Path):
    # Crear estructura: root / entregas / student1 / r1
    # y root / _baseline
    root = tmp_path / "workspace"
    root.mkdir()
    baseline = root / "_baseline"
    baseline.mkdir()

    entregas = root / "entregas"
    entregas.mkdir()
    student = entregas / "alumno_1"
    student.mkdir()
    r1 = student / "r1"
    r1.mkdir()

    # Buscar desde r1 debe encontrar root / _baseline
    found = find_baseline_dir(r1)
    assert found == baseline

    # Si pasamos explicit_baseline, debe priorizarlo
    custom_baseline = tmp_path / "custom_baseline"
    custom_baseline.mkdir()
    found_custom = find_baseline_dir(r1, explicit_baseline=custom_baseline)
    assert found_custom == custom_baseline.resolve()


def test_resolve_baseline_revision(tmp_path: Path):
    baseline_root = tmp_path / "_baseline"
    baseline_root.mkdir()
    r1 = baseline_root / "r1"
    r1.mkdir()
    r2 = baseline_root / "r2"
    r2.mkdir()

    # Si se pide r2
    assert resolve_baseline_revision(baseline_root, "r2") == r2
    # Si no se pide revisión, por defecto usa r1 si existe
    assert resolve_baseline_revision(baseline_root) == r1


def test_classify_submission_exercises_modular(tmp_path: Path):
    # Setup de baseline
    baseline_dir = tmp_path / "_baseline" / "r1"
    baseline_dir.mkdir(parents=True)
    (baseline_dir / "ejercicio1.c").write_text("/* Plantilla ej1 */\n", encoding="utf-8")
    (baseline_dir / "ejercicio2.c").write_text("/* Plantilla ej2 */\n", encoding="utf-8")

    # Setup de entrega de alumno con ejercicio1 modificado y ejercicio2 intacto
    student_rev = tmp_path / "alumno_test" / "r1"
    ej1_dir = student_rev / "ejercicios" / "ejercicio1"
    ej1_dir.mkdir(parents=True)
    (ej1_dir / "ejercicio1.c").write_text("int f(void) { return 1; }\n", encoding="utf-8")

    ej2_dir = student_rev / "ejercicios" / "ejercicio2"
    ej2_dir.mkdir(parents=True)
    (ej2_dir / "ejercicio2.c").write_text("/* Plantilla ej2 */\n", encoding="utf-8")

    info = classify_submission_exercises(student_rev, baseline_dir=tmp_path / "_baseline")
    assert info["has_baseline"] is True
    assert "ejercicio1" in info["completed"]
    assert "ejercicio2" in info["uncompleted"]
    assert info["status_by_exercise"]["ejercicio1"]["completed"] is True
    assert info["status_by_exercise"]["ejercicio2"]["completed"] is False


def test_classify_submission_exercises_flat(tmp_path: Path):
    baseline_dir = tmp_path / "_baseline" / "r1"
    baseline_dir.mkdir(parents=True)
    (baseline_dir / "ejercicio1.c").write_text("/* Plantilla ej1 */\n", encoding="utf-8")
    (baseline_dir / "ejercicio2.c").write_text("/* Plantilla ej2 */\n", encoding="utf-8")

    student_rev = tmp_path / "alumno_flat" / "r1"
    student_rev.mkdir(parents=True)
    (student_rev / "ejercicio1.c").write_text("int f(void) { return 1; }\n", encoding="utf-8")
    (student_rev / "ejercicio2.c").write_text("/* Plantilla ej2 */\n", encoding="utf-8")

    info = classify_submission_exercises(student_rev, baseline_dir=tmp_path / "_baseline")
    assert info["has_baseline"] is True
    assert "ejercicio1" in info["completed"]
    assert "ejercicio2" in info["uncompleted"]


def test_evaluate_makefile_exercises_skips_uncompleted(tmp_path: Path, monkeypatch):
    # Simular ejecución de makefile_eval asegurando que sólo se evalúen los ejercicios completados
    student_rev = tmp_path / "alumno" / "r1"
    ej1 = student_rev / "ejercicios" / "ejercicio1"
    ej1.mkdir(parents=True)
    (ej1 / "Makefile").write_text("all:\n\nclean:\n\ntest:\n", encoding="utf-8")

    ej2 = student_rev / "ejercicios" / "ejercicio2"
    ej2.mkdir(parents=True)
    (ej2 / "Makefile").write_text("all:\n\nclean:\n\ntest:\n", encoding="utf-8")

    calls = []

    def mock_run(cmd, *args, **kwargs):
        calls.append(cmd)

        class Res:
            returncode = 0
            stdout = "Mock OK"
            stderr = ""

        return Res()

    monkeypatch.setattr("subprocess.run", mock_run)

    # Filtrando ejercicio2
    results = evaluate_makefile_exercises(
        student_rev,
        uncompleted_exercises={"ejercicio2"},
    )
    assert len(results) == 1
    assert results[0].exercise_name == "ejercicio1"
    # Verificar que las llamadas a make apuntaron a ejercicio1 y nunca a ejercicio2
    assert any("ejercicio1" in str(c) for c in calls)
    assert not any("ejercicio2" in str(c) for c in calls)


def test_plagiarism_ignores_baseline_dir(tmp_path: Path):
    from dredd.core.plagiarism import PlagiarismDetector

    entregas = tmp_path / "entregas"
    entregas.mkdir()

    # Directorio _baseline
    b_dir = entregas / "_baseline"
    b_dir.mkdir()
    (b_dir / "plantilla.c").write_text("void plantilla(void) {}\n", encoding="utf-8")

    # Alumno 1
    a1 = entregas / "alumno1"
    a1.mkdir()
    (a1 / "code.c").write_text("int main(void) { return 0; }\n", encoding="utf-8")

    # Alumno 2
    a2 = entregas / "alumno2"
    a2.mkdir()
    (a2 / "code.c").write_text("int main(void) { return 1; }\n", encoding="utf-8")

    detector = PlagiarismDetector(threshold=0.5)
    matches = detector.analyze_submissions(entregas)

    # Verificar que _baseline no fue tratado como estudiante
    checked_students = set()
    for m in matches:
        checked_students.add(m.student_a)
        checked_students.add(m.student_b)
    assert "_baseline" not in checked_students


def test_cli_eval_skips_baseline_folder(tmp_path: Path, monkeypatch):
    from typer.testing import CliRunner
    from dredd.cli import app

    runner = CliRunner()
    monkeypatch.chdir(tmp_path)

    entregas = tmp_path / "entrega_test"
    entregas.mkdir()

    # Directorio _baseline
    b_dir = entregas / "_baseline"
    b_dir.mkdir()
    (b_dir / "plantilla.c").write_text("int f(void);\n")

    # Alumno real
    est = entregas / "alumno_real"
    est.mkdir()
    (est / "main.c").write_text("int main(void) { return 0; }\n")

    res = runner.invoke(app, ["eval", "entrega_test", "--all"])
    assert res.exit_code == 0
    assert "alumno_real" in res.output
    # Asegurar que _baseline NO aparece como estudiante evaluado en la salida
    assert "Procesando estudiante: _baseline" not in res.output
    assert not (b_dir / "_baseline_r1.md").exists()
    assert (est / "alumno_real_r1.md").is_file()


