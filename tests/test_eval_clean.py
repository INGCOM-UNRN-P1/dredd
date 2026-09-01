"""Tests unitarios e integrales para el comando dredd evaluate clean."""

from pathlib import Path
import pytest
from typer.testing import CliRunner

from dredd.cli import app
from dredd.core.eval_clean import (
    es_directorio_rni,
    es_archivo_informe,
    limpiar_evaluaciones_estudiante,
    limpiar_evaluaciones,
)

runner = CliRunner()


def test_es_directorio_rni(tmp_path: Path):
    r1i = tmp_path / "r1i"
    r1i.mkdir()
    r2i = tmp_path / "R2I"
    r2i.mkdir()
    r10i = tmp_path / "r10i"
    r10i.mkdir()

    no_rni1 = tmp_path / "r1"
    no_rni1.mkdir()
    no_rni2 = tmp_path / "r1_f"
    no_rni2.mkdir()
    no_rni3 = tmp_path / "src"
    no_rni3.mkdir()

    assert es_directorio_rni(r1i) is True
    assert es_directorio_rni(r2i) is True
    assert es_directorio_rni(r10i) is True
    assert es_directorio_rni(no_rni1) is False
    assert es_directorio_rni(no_rni2) is False
    assert es_directorio_rni(no_rni3) is False


def test_es_archivo_informe(tmp_path: Path):
    rep_md = tmp_path / "garcia_ana_r1.md"
    rep_md.write_text("informe")
    rep_html = tmp_path / "informe_r2.html"
    rep_html.write_text("html")
    rep_pdf = tmp_path / "alumno_r1.pdf"
    rep_pdf.write_text("pdf")

    # Archivos protegidos y fuentes que nunca deben ser eliminados
    main_c = tmp_path / "main.c"
    main_c.write_text("int main(){}")
    header_h = tmp_path / "libreria.h"
    header_h.write_text("void f();")
    mkfile = tmp_path / "Makefile"
    mkfile.write_text("all:")
    readme = tmp_path / "README.md"
    readme.write_text("doc")

    assert es_archivo_informe(rep_md) is True
    assert es_archivo_informe(rep_html) is True
    assert es_archivo_informe(rep_pdf) is True

    assert es_archivo_informe(main_c) is False
    assert es_archivo_informe(header_h) is False
    assert es_archivo_informe(mkfile) is False
    assert es_archivo_informe(readme) is False


def test_limpiar_evaluaciones_dry_run_y_real(tmp_path: Path):
    student = tmp_path / "estudiante_demo"
    student.mkdir()
    (student / "main.c").write_text("int main(){}")
    (student / "Makefile").write_text("all:")

    r1i = student / "r1i"
    r1i.mkdir()
    (r1i / "resumen.md").write_text("resumen")
    (r1i / "daedalus.md").write_text("daedalus")

    inf_md = student / "estudiante_demo_r1.md"
    inf_md.write_text("reporte consolidado")

    # 1. Simulación (dry-run): no borra nada
    res_dry = limpiar_evaluaciones_estudiante(student, dry_run=True)
    assert len(res_dry["rni"]) == 1
    assert len(res_dry["informes"]) == 1
    assert r1i.exists()
    assert inf_md.exists()
    assert (student / "main.c").exists()

    # 2. Limpieza real
    res_real = limpiar_evaluaciones_estudiante(student, dry_run=False)
    assert len(res_real["rni"]) == 1
    assert len(res_real["informes"]) == 1
    assert not r1i.exists()
    assert not inf_md.exists()
    assert (student / "main.c").exists()
    assert (student / "Makefile").exists()


def test_limpiar_evaluaciones_flags_parciales(tmp_path: Path):
    s = tmp_path / "alumno_test"
    s.mkdir()
    r1i = s / "r1i"
    r1i.mkdir()
    (r1i / "resumen.md").write_text("resumen")
    inf = s / "alumno_test_r1.md"
    inf.write_text("informe")

    # Solo informes
    res = limpiar_evaluaciones_estudiante(s, dry_run=False, limpiar_rni=False, limpiar_informes=True)
    assert not inf.exists()
    assert r1i.exists()

    # Solo rNi
    res2 = limpiar_evaluaciones_estudiante(s, dry_run=False, limpiar_rni=True, limpiar_informes=False)
    assert not r1i.exists()


def test_cli_evaluate_clean(tmp_path: Path):
    entregas = tmp_path / "tp01"
    a1 = entregas / "alumno1"
    a1.mkdir(parents=True)
    (a1 / "main.c").write_text("int main(){}")
    (a1 / "r1i").mkdir()
    (a1 / "alumno1_r1.md").write_text("informe")

    a2 = entregas / "alumno2"
    a2.mkdir(parents=True)
    (a2 / "r1i").mkdir()
    (a2 / "alumno2_r1.md").write_text("informe")

    # Ejecución de dredd evaluate clean
    res = runner.invoke(app, ["evaluate", "clean", str(entregas), "-v"])
    assert res.exit_code == 0
    assert "Directorios rNi eliminados: 2" in res.stdout
    assert "Informes eliminados: 2" in res.stdout
    assert not (a1 / "r1i").exists()
    assert not (a2 / "r1i").exists()
    assert not (a1 / "alumno1_r1.md").exists()
    assert not (a2 / "alumno2_r1.md").exists()
    assert (a1 / "main.c").exists()


def test_cli_eval_clean_alias(tmp_path: Path):
    entregas = tmp_path / "tp02"
    a1 = entregas / "alumno_x"
    a1.mkdir(parents=True)
    (a1 / "r1i").mkdir()
    (a1 / "alumno_x_r1.md").write_text("informe")

    # Invocación directa como subcomando interceptado en dredd eval clean
    res = runner.invoke(app, ["eval", "clean", str(entregas)])
    assert res.exit_code == 0
    assert "Directorios rNi eliminados: 1" in res.stdout
    assert not (a1 / "r1i").exists()
    assert not (a1 / "alumno_x_r1.md").exists()
