"""Ensamblador de informes Markdown modulares para feedback en PRs y archivo docente."""

from pathlib import Path
from typing import Any, Dict
from dredd.core.git_ops import RepoMetadata


def generate_student_report(
    exercise: str,
    student: str,
    repo_path: Path,
    metadata: RepoMetadata,
    analysis: Dict[str, Any],
    template_dir: Path,
    output_file: Path,
) -> str:
    """Genera el informe Markdown estructurado ${estudiante}.md."""
    lines = []

    # 1. Header template
    header_file = template_dir / "header.md"
    if header_file.is_file():
        lines.append(header_file.read_text(encoding="utf-8", errors="replace").strip())
    else:
        lines.append(f"# Informe de Corrección — {exercise}")

    lines.append("\n## Repositorio")
    lines.append(f"**branch/revision:** `{metadata.branch}` `{metadata.revision}`")
    lines.append(f"**Fecha:** {metadata.date_str}")

    if metadata.files_list:
        lines.append("\n### Archivos contenidos")
        lines.append("```text")
        lines.append(metadata.files_list)
        lines.append("```")

    lines.append("\n## Análisis de Código C")

    # 2. Compilación
    comp = analysis.get("compilation", {})
    if comp.get("success"):
        lines.append("\n### Compilación (GCC)")
        lines.append("✓ Compilación exitosa sin errores bloqueantes.")
    else:
        lines.append("\n### Compilación (GCC) — [FALLÓ]")
        if comp.get("human_summary"):
            lines.append(f"**Diagnóstico:** {comp['human_summary']}")
        
        diags = comp.get("translated_diagnostics", [])
        if diags:
            lines.append("\n| Archivo:Línea | Severidad | Mensaje Traducido | Sugerencia |")
            lines.append("| :--- | :---: | :--- | :--- |")
            for d in diags:
                sug = d.get("suggestion", "")
                lines.append(f"| `{d.get('file')}:{d.get('line')}` | **{d.get('severity')}** | {d.get('translated_message')} | {sug} |")
        elif comp.get("raw_stderr"):
            lines.append("```text")
            lines.append(comp["raw_stderr"][:1000])
            lines.append("```")

    # 3. Reglas AST y Calidad P1
    ast_findings = analysis.get("ast_findings", [])
    if ast_findings:
        lines.append("\n### Observaciones de Calidad y Reglas P1")
        lines.append("\n| Regla | Ubicación | Severidad | Observación | Sugerencia |")
        lines.append("| :--- | :--- | :---: | :--- | :--- |")
        for f in ast_findings:
            sug = f.get("suggestion", "")
            lines.append(f"| `{f.get('rule_id')}` | `{f.get('file')}:{f.get('line')}` | {f.get('severity')} | {f.get('message')} | {sug} |")
    else:
        lines.append("\n### Observaciones de Calidad y Reglas P1")
        lines.append("✓ No se detectaron violaciones a las reglas de estilo de cátedra.")

    # 4. Pruebas Funcionales y Memoria
    tests = analysis.get("tests", {})
    if tests.get("total", 0) > 0:
        lines.append("\n### Pruebas Funcionales y Chequeo de Memoria")
        lines.append(f"**Resultado:** {tests.get('passed', 0)} / {tests.get('total', 0)} pruebas aprobadas.\n")
        lines.append("| Caso | Estado | Fuga de Memoria | Detalle |")
        lines.append("| :--- | :---: | :---: | :--- |")
        for tc in tests.get("cases", []):
            st = "✓ PASÓ" if tc.get("passed") else "✗ FALLÓ"
            leak = "SI (Leak)" if tc.get("memory_leak") else "NO"
            err = tc.get("sanitizer_error", "") or ""
            err_summary = err.splitlines()[0] if err else ("Timeout" if tc.get("timed_out") else "OK")
            lines.append(f"| `{tc.get('name')}` | **{st}** | {leak} | {err_summary} |")

    # 5. Footer template
    footer_file = template_dir / "footer.md"
    if footer_file.is_file():
        lines.append("\n" + footer_file.read_text(encoding="utf-8", errors="replace").strip())

    report_content = "\n".join(lines) + "\n"
    output_file.write_text(report_content, encoding="utf-8")
    return report_content
