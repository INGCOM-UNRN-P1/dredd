"""Unit and integration tests for saving full compilation logs alongside reports."""

from pathlib import Path
from dredd.core.git_ops import RepoMetadata
from dredd.core.reporter import (
    build_full_compilation_log,
    save_compilation_log,
    generate_student_report,
)
from dredd.core.eval_clean import es_archivo_informe, limpiar_evaluaciones_estudiante


def test_build_full_compilation_log_basic():
    analysis = {
        "compilation": {
            "success": True,
            "compiler_used": "gcc",
            "files": {
                "main.c": {
                    "success": True,
                    "compiler_used": "gcc",
                    "command": ["gcc", "-Wall", "-Wextra", "-std=c11", "main.c", "-o", "bin"],
                    "returncode": 0,
                    "full_output": "Compilación limpia.",
                }
            },
            "translated_diagnostics": [],
        }
    }
    log_txt = build_full_compilation_log(
        analysis=analysis,
        revision="r1",
        student="alvarez_juan",
        exercise="tp01",
    )
    assert "DREDD - SALIDA COMPLETA DE COMPILACIÓN" in log_txt
    assert "Revisión: r1" in log_txt
    assert "Estudiante: alvarez_juan" in log_txt
    assert "Actividad: tp01" in log_txt
    assert "main.c" in log_txt
    assert "Compilación limpia." in log_txt
    assert "Compilación exitosa" in log_txt or "Estado general: EXITOSA" in log_txt


def test_save_compilation_log_creates_files_with_revision(tmp_path: Path):
    analysis = {
        "compilation": {
            "success": False,
            "compiler_used": "gcc",
            "raw_stderr": "main.c:5:10: error: unknown type name 'foobar'",
            "translated_diagnostics": [
                {
                    "file": "main.c",
                    "line": 5,
                    "severity": "ERROR",
                    "translated_message": "Tipo de dato desconocido 'foobar'",
                    "suggestion": "Declarar o incluir el tipo.",
                }
            ],
        }
    }
    out_dir = tmp_path / "entregas" / "benavides_facundo"
    out_dir.mkdir(parents=True)

    saved = save_compilation_log(
        output_dir=out_dir,
        analysis=analysis,
        revision="r3",
        student="benavides_facundo",
        exercise="tp04",
        output_stem="benavides_facundo_r3",
    )

    canonical = out_dir / "compilacion_r3.log"
    student_log = out_dir / "benavides_facundo_r3_compilacion.log"

    assert canonical.is_file()
    assert student_log.is_file()
    assert canonical in saved

    content = canonical.read_text(encoding="utf-8")
    assert "Revisión: r3" in content
    assert "Estado general: FALLÓ" in content
    assert "unknown type name 'foobar'" in content
    assert "Tipo de dato desconocido 'foobar'" in content
    assert "Sugerencia: Declarar o incluir el tipo." in content


def test_generate_student_report_saves_compilation_log_in_same_location(tmp_path: Path):
    template_dir = tmp_path / "informe"
    template_dir.mkdir()
    (template_dir / "header.md").write_text("# Informe Header\n")

    student_dir = tmp_path / "submissions" / "gomez_lucas"
    student_dir.mkdir(parents=True)
    r1_dir = student_dir / "r1"
    r1_dir.mkdir()

    meta = RepoMetadata(branch="main", revision="abc999", date_str="2026-09-07")
    analysis = {
        "compilation": {
            "success": True,
            "compiler_used": "gcc",
            "files": {
                "ej1.c": {
                    "success": True,
                    "compiler_used": "gcc",
                    "full_output": "warning: unused variable 'x' [-Wunused-variable]",
                    "command": ["gcc", "-Wall", "ej1.c"],
                    "returncode": 0,
                }
            },
            "translated_diagnostics": [],
        },
        "ast_findings": [],
        "tests": {"total": 0},
    }

    report_file = student_dir / "gomez_lucas_r2.md"
    generate_student_report(
        exercise="tp02",
        student="gomez_lucas",
        repo_path=student_dir,
        metadata=meta,
        analysis=analysis,
        template_dir=template_dir,
        output_file=report_file,
        revision="r2",
    )

    # El informe existe
    assert report_file.is_file()

    # En la misma ubicación que el informe deben guardarse los logs de compilación con número de revisión
    comp_canonical = student_dir / "compilacion_r2.log"
    comp_student = student_dir / "gomez_lucas_r2_compilacion.log"
    assert comp_canonical.is_file()
    assert comp_student.is_file()

    log_txt = comp_canonical.read_text(encoding="utf-8")
    assert "Revisión: r2" in log_txt
    assert "unused variable 'x'" in log_txt

    # También se guarda copia en r2i para auditoría modular
    assert (student_dir / "r2i" / "compilacion_r2.log").is_file()


def test_eval_clean_detects_and_removes_compilation_logs(tmp_path: Path):
    student_dir = tmp_path / "alumno_test"
    student_dir.mkdir()
    (student_dir / "main.c").write_text("int main(){ return 0; }")

    inf_md = student_dir / "alumno_test_r1.md"
    inf_md.write_text("reporte")

    comp_log1 = student_dir / "compilacion_r1.log"
    comp_log1.write_text("log r1")

    comp_log2 = student_dir / "alumno_test_r1_compilacion.log"
    comp_log2.write_text("log student r1")

    # Archivo ajeno protegido
    unrelated_log = student_dir / "unrelated.log"
    unrelated_log.write_text("system log")

    assert es_archivo_informe(inf_md) is True
    assert es_archivo_informe(comp_log1) is True
    assert es_archivo_informe(comp_log2) is True
    assert es_archivo_informe(unrelated_log) is False

    res = limpiar_evaluaciones_estudiante(student_dir, dry_run=False)
    assert not inf_md.exists()
    assert not comp_log1.exists()
    assert not comp_log2.exists()
    assert unrelated_log.exists()
    assert (student_dir / "main.c").exists()
