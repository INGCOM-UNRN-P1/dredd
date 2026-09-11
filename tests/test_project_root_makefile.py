"""Tests para la ejecución exclusiva del Makefile raíz en entregas tipo proyecto."""

from pathlib import Path
import subprocess
from dredd.core.config import DreddConfig, MODE_PROYECTO
from dredd.core.ripley_client import run_ripley_analysis
from dredd.core.reporter import generate_student_report, generate_personalized_feedback_markdown
from dredd.core.git_ops import RepoMetadata


def test_get_delivery_mode_prioritizes_root_makefile(tmp_path: Path):
    cfg = DreddConfig()
    student_dir = tmp_path / "entrega_con_todo"
    student_dir.mkdir()

    # Makefile en la raíz
    (student_dir / "Makefile").write_text("all:\n\t@echo 'root makefile all'\ntest:\n\t@echo 'root makefile test'\n")

    # Sub-makefiles en subdirectorios
    sub1 = student_dir / "ejercicio1"
    sub1.mkdir()
    (sub1 / "Makefile").write_text("all:\n\t@echo 'sub1'\n")

    sub2 = student_dir / "ejercicio2"
    sub2.mkdir()
    (sub2 / "Makefile").write_text("all:\n\t@echo 'sub2'\n")

    # Debe clasificar como MODE_PROYECTO priorizando el Makefile raíz
    mode = cfg.get_delivery_mode(activity_slug="tp01", target_path=student_dir)
    assert mode == MODE_PROYECTO


def test_project_root_makefile_execution_and_simplified_report(tmp_path: Path, monkeypatch):
    student_dir = tmp_path / "proyecto_estudiante"
    student_dir.mkdir()

    # Marcador para verificar si se ejecutó el sub-makefile
    sub_marker = student_dir / "sub_ejecutado.txt"
    sub_dir = student_dir / "ejercicio1"
    sub_dir.mkdir()
    (sub_dir / "Makefile").write_text(f"all:\n\ttouch {sub_marker.name}\nclean:\n\t@true\ntest:\n\ttouch {sub_marker.name}\n")

    # Makefile raíz del proyecto
    root_marker = student_dir / "root_ejecutado.txt"
    makefile_content = f"""all:
\ttouch {root_marker.name}

test:
\t@echo "suite del proyecto aprobada"

clean:
\t@true
"""
    (student_dir / "Makefile").write_text(makefile_content)
    (student_dir / "main.c").write_text("int main(void) { return 0; }\n")

    # Ejecutar análisis en modo proyecto
    analysis = run_ripley_analysis(
        student_dir,
        activity_slug="tp_proyecto",
        tipo_entrega=MODE_PROYECTO,
    )

    # 1. El Makefile raíz debe haberse ejecutado
    assert root_marker.is_file()

    # 2. El sub-makefile NO debe haberse ejecutado
    assert not sub_marker.is_file()

    # 3. La compilación y los tests deben reflejar el modo proyecto
    assert analysis["compilation"]["success"] is True
    assert analysis["compilation"]["is_project"] is True
    assert analysis["tests"]["is_project"] is True
    assert analysis["tests"]["has_test_target"] is True
    assert analysis["tests"]["passed"] == 1

    # 4. Generar informe y verificar formato simplificado
    meta = RepoMetadata(
        branch="main",
        revision="abc1234",
        full_hash="abc1234567890",
        author="Alumno Test",
        commit_date="2026-09-11",
        commit_message="Entrega proyecto",
        date_str="2026-09-11 12:00:00",
        files_list="Makefile\nmain.c\nejercicio1/Makefile",
        recent_commits=["abc1234 Entrega proyecto"],
    )

    rni_dir = student_dir / "r1i"
    report_file = student_dir / "proyecto_estudiante_r1.md"
    template_dir = tmp_path / "templates"
    template_dir.mkdir()

    rep_content = generate_student_report(
        exercise="tp_proyecto",
        student="proyecto_estudiante",
        repo_path=student_dir,
        metadata=meta,
        analysis=analysis,
        template_dir=template_dir,
        output_file=report_file,
        revision="r1",
        intermediate_dir=rni_dir,
    )

    # Verificar daedalus.md y tests.md simplificados
    daed_text = (rni_dir / "daedalus.md").read_text(encoding="utf-8")
    assert "Compilación — Makefile raíz del Proyecto" in daed_text
    assert "Compilación exitosa ejecutando el Makefile en la raíz (`make`)" in daed_text
    assert "Estado de Compilación por Archivo" not in daed_text

    tests_text = (rni_dir / "tests.md").read_text(encoding="utf-8")
    assert "Pruebas del Proyecto — Makefile raíz (`make test`)" in tests_text
    assert "Pruebas del proyecto aprobadas con éxito (`make test`)" in tests_text

    # Verificar feedback simplificado
    fb_text = generate_personalized_feedback_markdown(
        student_name="proyecto_estudiante",
        exercise_name="tp_proyecto",
        analysis=analysis,
        metadata=meta,
        revision="r1",
    )
    assert "- **Compilación (Makefile raíz):** ✓ Exitosa" in fb_text
    assert "- **Pruebas de proyecto (make test):** ✓ Aprobadas" in fb_text
