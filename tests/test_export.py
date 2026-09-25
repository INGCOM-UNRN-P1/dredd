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


# ── N-DREDD-01: el parser no debe colgarse con líneas que solo empiezan con `#` o `|` ──

import multiprocessing
import resource

import pytest


def _parsea_en_hijo(md: str) -> None:
    # Un bucle infinito que acumula bloques agotaría la memoria del host:
    # el hijo la tiene acotada y el padre lo mata si no termina a tiempo.
    resource.setrlimit(resource.RLIMIT_AS, (512 * 1024 * 1024, 512 * 1024 * 1024))
    parse_markdown(md)


def _termina(md: str, segundos: float = 5.0) -> bool:
    hijo = multiprocessing.get_context("fork").Process(target=_parsea_en_hijo, args=(md,))
    hijo.start()
    hijo.join(segundos)
    if hijo.is_alive():
        hijo.kill()
        hijo.join()
        return False
    return hijo.exitcode == 0


@pytest.mark.parametrize(
    "md",
    [
        "# Informe\n\n#### Detalle\n\ntexto\n",
        "#include <stdio.h>\nint main(void) { return 0; }\n",
        "texto\n#hashtag sin espacio\nmás texto\n",
        "| tabla sin cierre\n| otra fila\n",
        "*énfasis* al comienzo\n",
        "-sin espacio tras el guion\n",
    ],
)
def test_parse_markdown_siempre_termina(md: str):
    assert _termina(md), "parse_markdown no terminó (bucle infinito o sin memoria)"
    assert parse_markdown(md)


def test_parse_markdown_encabezados_h4_a_h6():
    md = "#### Cuatro\n\n##### Cinco\n\n###### Seis\n"
    assert _termina(md)
    bloques = parse_markdown(md)
    assert [(b.kind, b.level, b.text) for b in bloques] == [("h", 4, "Cuatro"), ("h", 5, "Cinco"), ("h", 6, "Seis")]
    assert "<h4>Cuatro</h4>" in render_html_report(bloques)


def test_parse_markdown_include_es_texto_del_parrafo():
    md = "Encabezado del programa:\n#include <stdio.h>\n"
    assert _termina(md)
    bloques = parse_markdown(md)
    assert len(bloques) == 1
    assert bloques[0].kind == "p"
    assert "#include <stdio.h>" in bloques[0].text


def test_export_report_de_un_fuente_c_no_se_cuelga(tmp_path: Path):
    fuente = tmp_path / "lista.c"
    fuente.write_text("#include <stdio.h>\n#include \"lista.h\"\n\nint main(void)\n{\n    return 0;\n}\n")
    assert _termina(fuente.read_text())
    salida = export_report(fuente, fmt="html", out_path=tmp_path / "lista.html")
    assert Path(salida).exists()
