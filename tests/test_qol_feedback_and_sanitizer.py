"""Tests para las mejoras QoL: report_template y sanitize_output en Dredd."""

from pathlib import Path
import pytest
from typer.testing import CliRunner

from dredd.cli import app
from dredd.core.output_sanitizer import sanitize_output, sanitize_log_file
from dredd.core.feedback_template import (
    render_feedback_template,
    extract_context_from_analysis,
    load_and_render_feedback_template,
)
from dredd.core.reporter import generate_personalized_feedback_markdown

runner = CliRunner()


def test_sanitize_output_ansi_and_control():
    # ANSI escape code (ej. colores y cursor)
    raw_ansi = "\x1B[31mError fatal\x1B[0m en \x1B[1mmain.c\x1B[0m\n"
    clean = sanitize_output(raw_ansi)
    assert clean == "Error fatal en main.c\n"
    assert "\x1B" not in clean

    # Caracteres de control corruptos preservando tab y newline
    raw_control = "Hola\x00\x07Mundo\t123\n\x0B"
    clean_ctrl = sanitize_output(raw_control)
    assert clean_ctrl == "HolaMundo\t123\n"


def test_sanitize_output_truncation(tmp_path: Path):
    # Truncado seguro por tamaño
    big_data = "A" * 500
    cleaned = sanitize_output(big_data, max_bytes=100)
    assert len(cleaned) < 300
    assert "AVISO: Salida truncada automáticamente" in cleaned
    assert cleaned.startswith("A" * 100)

    # Sanitización de archivo en disco
    log_file = tmp_path / "student_build.log"
    log_file.write_text("\x1B[32mCompilando...\x1B[0m\x00\x00\nOK\n", encoding="utf-8")
    sanitized_file = tmp_path / "student_clean.log"
    sanitize_log_file(log_file, output_path=sanitized_file)

    content = sanitized_file.read_text(encoding="utf-8")
    assert content == "Compilando...\nOK\n"


def test_render_feedback_template_variables():
    tmpl = (
        "# Feedback {student_name}\n"
        "ID: {student_id}\n"
        "Nota: {score}/10\n"
        "Pruebas: {passed_tests}/{total_tests}\n"
        "Badge: {badge}\n"
        "Fugas: {memory_summary}\n"
        "Detalle: {failures}\n"
    )
    context = {
        "student_name": "Juan Perez",
        "student_id": "jperez",
        "score": "8.5",
        "passed_tests": 8,
        "total_tests": 10,
        "badge": "APROBADO",
        "memory_summary": "Sin fugas",
        "failures": "Caso 2 falló",
    }
    rendered = render_feedback_template(tmpl, context)
    assert "Juan Perez" in rendered
    assert "ID: jperez" in rendered
    assert "Nota: 8.5/10" in rendered
    assert "Pruebas: 8/10" in rendered
    assert "Badge: APROBADO" in rendered
    assert "Fugas: Sin fugas" in rendered


def test_extract_context_and_load_template(tmp_path: Path):
    analysis = {
        "compilation": {"success": True, "compiler_used": "gcc"},
        "ast_findings": [],
        "tests": {
            "total": 5,
            "passed": 4,
            "failed": 1,
            "cases": [
                {"name": "caso_01", "passed": True},
                {"name": "caso_02", "passed": False, "error_message": "Salida errónea"},
            ],
        },
        "valgrind": {"executed": True, "clean": False, "definitely_lost_bytes": 64},
        "binary_findings": [],
    }

    ctx = extract_context_from_analysis(analysis, student_name="Ana Gomez", exercise_name="tp1")
    assert ctx["student_name"] == "Ana Gomez"
    assert ctx["total_tests"] == 5
    assert ctx["passed_tests"] == 4
    assert ctx["failed_tests"] == 1
    assert "64 bytes definitivamente perdidos" in ctx["memory_summary"]
    assert "caso_02" in ctx["failures"]

    # Con archivo de template custom
    custom_tmpl = tmp_path / "custom_feedback.md"
    custom_tmpl.write_text("Estudiante: {student_name} - Puntaje: {score}", encoding="utf-8")
    result = load_and_render_feedback_template(custom_tmpl, ctx)
    assert "Estudiante: Ana Gomez - Puntaje:" in result

    # Integración con generate_personalized_feedback_markdown
    direct_markdown = generate_personalized_feedback_markdown(
        student_name="Ana Gomez",
        exercise_name="tp1",
        analysis=analysis,
        template_path=custom_tmpl,
    )
    assert "Estudiante: Ana Gomez" in direct_markdown


def test_cli_report_template_and_sanitize(tmp_path: Path):
    # 1. Probar cli report-template
    res_tmpl = runner.invoke(
        app,
        [
            "report-template",
            "--student", "alumno_test",
            "--score", "9.5",
            "--total-tests", "4",
            "--passed-tests", "4",
        ],
    )
    assert res_tmpl.exit_code == 0
    assert "alumno_test" in res_tmpl.output
    assert "9.5" in res_tmpl.output

    # 2. Probar cli report-template dump-default
    res_dump = runner.invoke(app, ["report-template", "--dump-default"])
    assert res_dump.exit_code == 0
    assert "{student_name}" in res_dump.output

    # 3. Probar cli sanitize-output
    dirty_log = tmp_path / "dirty.log"
    dirty_log.write_text("\x1B[33mAdvertencia\x1B[0m\n", encoding="utf-8")
    clean_log = tmp_path / "clean.log"

    res_san = runner.invoke(app, ["sanitize-output", str(dirty_log), "--output", str(clean_log)])
    assert res_san.exit_code == 0
    assert clean_log.is_file()
    assert clean_log.read_text(encoding="utf-8") == "Advertencia\n"
