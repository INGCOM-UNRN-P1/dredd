"""Unit tests for Dredd Moodle exporter, cohort dashboard, and report export (HTML/PDF)."""

from pathlib import Path

from dredd.core.db import DatabaseManager, StudentRecord
from dredd.core.exporter import MoodleExporter
from dredd.core.report_export import export_report, render_html_report, render_pdf_report, parse_markdown


def test_moodle_exporter(tmp_path: Path):
    act_slug = "tp1_100"
    act_dir = tmp_path / act_slug
    student_dir = act_dir / "perez-juan_123"
    student_dir.mkdir(parents=True, exist_ok=True)

    db = DatabaseManager(student_dir / ".metadata.db")
    db.upsert_student(StudentRecord("123", "Perez Juan", "perez-juan_123", "999"))
    rev_id = db.add_revision(
        student_slug="perez-juan_123",
        version_num=1,
        sources_hash="hash1",
        folder_path=str(student_dir / "r1"),
        sources=[],
        ignored=[],
    )
    db.save_evaluation(
        revision_id=rev_id,
        compilation_status="OK",
        preliminary_grade=9.5,
        grade_compilation=10.0,
        grade_style=9.0,
        grade_linter=10.0,
        grade_tests=9.5,
        unified_diff="",
        compilation_logs="",
        test_results=[],
    )
    (student_dir / "perez-juan_123_tp1_100.md").write_text("# Informe Perez\n\nTodo OK.", encoding="utf-8")

    exporter = MoodleExporter(workspace_dir=tmp_path)
    csv_file = exporter.export_grades_csv(act_slug)
    zip_file = exporter.export_feedback_zip(act_slug)
    dash_file = exporter.generate_dashboard(act_slug)

    assert csv_file.exists()
    assert zip_file.exists()
    assert dash_file.exists()

    csv_content = csv_file.read_text(encoding="utf-8-sig")
    assert "Perez Juan" in csv_content
    assert "9.50" in csv_content

    dash_content = dash_file.read_text(encoding="utf-8")
    assert "100.0%" in dash_content
    assert "Perez Juan" in dash_content


def test_report_export_html_and_pdf(tmp_path: Path):
    md_file = tmp_path / "informe.md"
    md_file.write_text(
        """# Informe de Evaluación
## Resumen
- **Compilación**: OK
- **Estilo**: 10/10

```c
int main() { return 0; }
```

| Métrica | Valor |
| --- | --- |
| Nota | 10 |
""",
        encoding="utf-8",
    )

    html_out = export_report(md_file, fmt="html")
    assert html_out.exists()
    html_text = html_out.read_text(encoding="utf-8")
    assert "<!DOCTYPE html>" in html_text
    assert "Informe de Evaluación" in html_text

    pdf_out = export_report(md_file, fmt="pdf")
    assert pdf_out.exists()
    pdf_bytes = pdf_out.read_bytes()
    assert pdf_bytes.startswith(b"%PDF-1.4")
