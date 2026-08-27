"""Unit tests for Dredd report generation."""

from pathlib import Path
from dredd.core.git_ops import RepoMetadata
from dredd.core.reporter import generate_student_report


def test_generate_student_report(tmp_path: Path):
    template_dir = tmp_path / "informe"
    template_dir.mkdir()
    (template_dir / "header.md").write_text("# Encabezado Institucional\n")
    (template_dir / "footer.md").write_text("## Criterios de Evaluación\n")

    repo_path = tmp_path / "repo"
    repo_path.mkdir()

    meta = RepoMetadata(branch="main", revision="abc1234", date_str="2026-08-24 10:00:00", files_list="- main.c")
    analysis = {
        "compilation": {
            "success": True,
            "translated_diagnostics": [],
        },
        "ast_findings": [
            {
                "rule_id": "0x0001h",
                "file": "main.c",
                "line": 10,
                "severity": "ADVERTENCIA",
                "message": "Nombre de variable poco descriptivo",
                "suggestion": "Usar nombres más claros",
            }
        ],
        "tests": {
            "total": 2,
            "passed": 2,
            "cases": [
                {"name": "caso_01", "passed": True, "memory_leak": False, "sanitizer_error": ""},
                {"name": "caso_02", "passed": True, "memory_leak": False, "sanitizer_error": ""},
            ],
        },
    }

    out_file = tmp_path / "alvarez_juan.md"
    content = generate_student_report(
        exercise="tp01",
        student="alvarez_juan",
        repo_path=repo_path,
        metadata=meta,
        analysis=analysis,
        template_dir=template_dir,
        output_file=out_file,
    )

    assert out_file.exists()
    assert "# Encabezado Institucional" in content
    assert "abc1234" in content
    assert "0x0001h" in content
    assert "2 / 2 pruebas aprobadas" in content
    assert "## Criterios de Evaluación" in content


def test_generate_student_report_with_revision(tmp_path: Path):
    template_dir = tmp_path / "informe"
    template_dir.mkdir()
    repo_path = tmp_path / "repo"
    repo_path.mkdir()

    meta = RepoMetadata(branch="main", revision="rev123", date_str="2026-08-27")
    analysis = {"compilation": {"success": True}, "ast_findings": [], "tests": {"total": 0}}
    out_file = repo_path / "perez_r2.md"

    content = generate_student_report(
        exercise="tp02",
        student="perez",
        repo_path=repo_path,
        metadata=meta,
        analysis=analysis,
        template_dir=template_dir,
        output_file=out_file,
        revision="r2",
    )
    assert out_file.is_file()
    assert "**Versión revisada:** `r2`" in content
    assert "tp02 (r2)" in content


def test_resolve_submission_revision_and_find_report(tmp_path: Path):
    from dredd.core.reporter import resolve_submission_revision, find_student_report
    from dredd.core.db import DatabaseManager, StudentRecord

    student_dir = tmp_path / "tp01-submissions" / "garcia_ana"
    student_dir.mkdir(parents=True)

    # 1. Sin db ni subcarpetas: default r1
    assert resolve_submission_revision(student_dir, "garcia_ana") == "r1"

    # 2. Con .metadata.db y revision r3
    db = DatabaseManager(student_dir / ".metadata.db")
    db.upsert_student(StudentRecord("1", "Ana Garcia", "garcia_ana", "sub1"))
    db.add_revision("garcia_ana", 3, "hash3", str(student_dir), [], [])

    assert resolve_submission_revision(student_dir, "garcia_ana") == "r3"

    # 3. Guardar informe y verificar find_student_report
    report_file = student_dir / "garcia_ana_r3.md"
    report_file.write_text("# Informe Ana r3\n", encoding="utf-8")

    encontrado = find_student_report(tmp_path, "tp01", "garcia_ana")
    assert encontrado == report_file

