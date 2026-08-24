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
