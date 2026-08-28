"""Ensamblador de informes Markdown modulares para feedback en PRs y archivo docente."""

from pathlib import Path
import re
from typing import Any, Dict, Optional
from dredd.core.git_ops import RepoMetadata


def resolve_submission_revision(repo_path: Path, student_slug: str) -> str:
    """Determina la versión revisada (r1, r2, etc.) para la entrega del estudiante."""
    from dredd.core.db import DatabaseManager

    # 1. Base de datos SQLite .metadata.db en la carpeta del estudiante o en la carpeta padre
    for db_cand in [repo_path / ".metadata.db", repo_path.parent / ".metadata.db"]:
        if db_cand.is_file():
            try:
                db = DatabaseManager(db_cand)
                rev = db.get_latest_revision(student_slug)
                if rev and rev["version_num"]:
                    return f"r{rev['version_num']}"
            except Exception:
                pass

    # 2. Si la carpeta misma es rN o rN_f (ej: .../alumno1/r1_f o .../alumno1/r1)
    m_self = re.match(r"^r(\d+)(?:_f)?$", repo_path.name, re.IGNORECASE)
    if m_self:
        return f"r{m_self.group(1)}"

    # 3. Si contiene subcarpetas rN o rN_f
    if repo_path.is_dir():
        rev_nums = []
        for d in repo_path.iterdir():
            if d.is_dir():
                m_sub = re.match(r"^r(\d+)(?:_f)?$", d.name, re.IGNORECASE)
                if m_sub:
                    rev_nums.append(int(m_sub.group(1)))
        if rev_nums:
            return f"r{max(rev_nums)}"

    # 4. Si ya existen informes rN en la carpeta
    if repo_path.is_dir():
        existing_reports = list(repo_path.glob("*_r*.md")) + list(repo_path.glob("r*.md"))
        if existing_reports:
            versions = []
            for rep in existing_reports:
                m = re.search(r"r(\d+)", rep.stem)
                if m:
                    versions.append(int(m.group(1)))
            if versions:
                return f"r{max(versions)}"

    # 5. Default
    return "r1"


def find_student_report(workspace_dir: Path, exercise: str, student: str) -> Optional[Path]:
    """Busca el informe Markdown generado más reciente para el estudiante."""
    from dredd.core.git_ops import resolve_submissions_dir

    _, submissions_dir = resolve_submissions_dir(workspace_dir, exercise)
    student_dir = submissions_dir / student

    if student_dir.is_dir():
        candidates = []
        for pat in [f"{student}_r*.md", "informe_r*.md", f"*_{student}_r*.md", "*.md"]:
            for f in sorted(student_dir.glob(pat)):
                if f.is_file() and not f.name.startswith("."):
                    candidates.append(f)
        if candidates:
            candidates.sort(key=lambda p: (p.stat().st_mtime, p.name), reverse=True)
            return candidates[0]

    root_cand = [
        workspace_dir / f"{student}.md",
        workspace_dir / f"{student}_r1.md",
    ]
    for c in root_cand:
        if c.is_file():
            return c

    return None


def generate_student_report(
    exercise: str,
    student: str,
    repo_path: Path,
    metadata: RepoMetadata,
    analysis: Dict[str, Any],
    template_dir: Path,
    output_file: Path,
    revision: Optional[str] = None,
    guide: Optional[Any] = None,
) -> str:
    """Genera el informe Markdown estructurado en la carpeta de la entrega con su versión (r1, r2, etc.)."""
    lines = []

    # 1. Header template
    header_file = template_dir / "header.md"
    if header_file.is_file():
        lines.append(header_file.read_text(encoding="utf-8", errors="replace").strip())
    else:
        rev_title = f" ({revision})" if revision else ""
        lines.append(f"# Informe de Corrección — {exercise}{rev_title}")

    lines.append("\n## Repositorio")
    lines.append(f"**branch/revision:** `{metadata.branch}` `{metadata.revision}`")
    lines.append(f"**Fecha:** {metadata.date_str}")
    if revision:
        lines.append(f"**Versión revisada:** `{revision}`")

    if guide and getattr(guide, "exercises", None):
        lines.append("\n## Especificación de la Guía")
        lines.append(f"**Guía vinculada:** `{guide.nombre}`")
        ejs_str = ", ".join(f"`{e.display_name}`" for e in guide.exercises)
        lines.append(f"**Ejercicios requeridos:** {ejs_str}")

    if metadata.files_list:
        lines.append("\n### Archivos contenidos")
        lines.append("```text")
        lines.append(metadata.files_list)
        lines.append("```")

    lines.append("\n## Análisis de Código C")

    # 2. Compilación
    comp = analysis.get("compilation", {})
    compiler_used = comp.get("compiler_used", "gcc").upper()
    comp_header = f"Compilación ({compiler_used})" if compiler_used != "NONE" else "Compilación"
    if comp.get("success"):
        lines.append(f"\n### {comp_header}")
        lines.append("✓ Compilación exitosa sin errores bloqueantes.")
    else:
        lines.append(f"\n### {comp_header} — [FALLÓ]")
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
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(report_content, encoding="utf-8")
    return report_content


def generate_personalized_feedback_markdown(
    student_name: str,
    exercise_name: str,
    analysis: Dict[str, Any],
    metadata: Optional[RepoMetadata] = None,
    guide: Optional[Any] = None,
    revision: Optional[str] = None,
) -> str:
    """Genera una devolución personalizada en Markdown lista para adjuntar en Moodle / GitHub Classroom PR."""
    comp = analysis.get("compilation", {})
    ast = analysis.get("ast_findings", [])
    tests = analysis.get("tests", {})

    passed = (
        comp.get("success", False)
        and (tests.get("failed", 0) == 0)
        and not any(f.get("severity") in ("ERROR", "FATAL") for f in ast)
    )

    status_badge = "✅ **ENTREGA APROBADA**" if passed else "⚠️ **ENTREGA CON OBSERVACIONES / REQUIERE REVISIÓN**"
    if not comp.get("success", False):
        status_badge = "❌ **ENTREGA NO APROBADA (Error de compilación)**"

    lines = [
        f"## Devolución Pedagógica — {student_name}",
        f"**Actividad:** `{exercise_name}`",
        f"**Estado General:** {status_badge}",
    ]

    if revision:
        lines.append(f"**Versión:** `{revision}`")

    lines.append("\n### 📋 Resumen de Evaluación")
    lines.append(f"- **Compilación ({comp.get('compiler_used', 'GCC').upper()}):** {'✓ Exitosa' if comp.get('success') else '✖ Falló'}")
    lines.append(f"- **Reglas P1 / Calidad:** {len(ast)} observación(es) detectada(s)")
    if tests.get("total", 0) > 0:
        lines.append(f"- **Casos de prueba:** {tests.get('passed', 0)}/{tests.get('total', 0)} aprobados")

    # Acciones concretas sugeridas
    issues = []
    if not comp.get("success"):
        issues.append("Corregir los errores de compilación antes de volver a entregar.")
    for d in comp.get("translated_diagnostics", []):
        if d.get("suggestion"):
            issues.append(d["suggestion"])
    for f in ast:
        if f.get("suggestion"):
            issues.append(f"{f.get('rule_code', 'P1')}: {f['suggestion']}")
    for tc in tests.get("cases", []):
        if not tc.get("passed"):
            issues.append(f"Revisar caso `{tc.get('name')}`: verificar lógica o manejo de límites.")

    if issues:
        lines.append("\n### 🔧 Pasos sugeridos para la próxima entrega:")
        for idx, iss in enumerate(issues[:6], 1):
            lines.append(f"{idx}. {iss}")

    lines.append("\n---\n*Cátedra de Programación 1 · Evaluación automatizada con Dredd*")
    return "\n".join(lines) + "\n"

