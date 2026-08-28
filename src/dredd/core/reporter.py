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


def write_individual_tool_reports(
    rni_dir: Path,
    analysis: Dict[str, Any],
    metadata: Optional[RepoMetadata] = None,
    guide: Optional[Any] = None,
) -> Dict[str, Path]:
    """Genera los informes individuales en Markdown para cada herramienta en el directorio rNi."""
    rni_dir.mkdir(parents=True, exist_ok=True)
    generated: Dict[str, Path] = {}

    # 0. Resumen de Evaluación por Archivo (resumen.md)
    comp = analysis.get("compilation", {})
    files_comp = comp.get("files", {})
    ast_findings = analysis.get("ast_findings", [])
    style_findings = analysis.get("style_findings", [])
    tests = analysis.get("tests", {})
    cases = tests.get("cases", [])
    val = analysis.get("valgrind", {})

    all_c_files = set(files_comp.keys())
    for f in ast_findings:
        if f.get("file"):
            all_c_files.add(f.get("file"))
    for sf in style_findings:
        if sf.get("file"):
            all_c_files.add(sf.get("file"))

    if not all_c_files:
        all_c_files.add("entrega_general")

    res_lines = ["## Resumen de Evaluación por Archivo\n"]
    res_lines.append("| Archivo | Estado Compilación | Evaluación de Estilo | Valgrind (Fugas) | Observaciones Cátedra |")
    res_lines.append("| :--- | :---: | :---: | :---: | :--- |")
    for f_name in sorted(all_c_files):
        # Compilación
        f_comp_ok = files_comp.get(f_name, {}).get("success", comp.get("success", True))
        comp_badge = "✓ Compilación OK" if f_comp_ok else "❌ Falló Compilación"

        # Estilo
        f_style_viols = [sf for sf in style_findings if sf.get("file") == f_name]
        style_score = max(0.0, 10.0 - (len(f_style_viols) * 0.5))
        style_badge = f"{style_score:.1f}/10"

        # Valgrind
        f_val_leak = any(c.get("memory_leak") for c in cases if f_name in c.get("name", ""))
        val_badge = "⚠️ Fuga detectada" if f_val_leak else "✓ Limpio (0 fugas)"

        # Reglas
        f_ast_viols = [af for af in ast_findings if af.get("file") == f_name]
        total_viols = len(f_style_viols) + len(f_ast_viols)
        obs_badge = f"{total_viols} advertencias" if total_viols > 0 else "Sin observaciones"

        res_lines.append(f"| `{f_name}` | {comp_badge} | {style_badge} | {val_badge} | {obs_badge} |")
    
    res_path = rni_dir / "resumen.md"
    res_path.write_text("\n".join(res_lines) + "\n", encoding="utf-8")
    generated["resumen"] = res_path

    # 1. Daedalus (Compilación)
    compiler_used = comp.get("compiler_used", "gcc").upper()
    comp_lines = [f"## Compilación — Daedalus ({compiler_used})"]
    if comp.get("success"):
        comp_lines.append("\n✓ **Estado:** Compilación exitosa sin errores bloqueantes.")
    else:
        comp_lines.append("\n❌ **Estado:** Falló la compilación.")
        if comp.get("human_summary"):
            comp_lines.append(f"\n**Diagnóstico general:** {comp['human_summary']}")

    if files_comp:
        comp_lines.append("\n### Estado de Compilación por Archivo")
        comp_lines.append("| Archivo | Estado | Compilador |")
        comp_lines.append("| :--- | :---: | :---: |")
        for f_name, f_data in sorted(files_comp.items()):
            st = "✓ OK" if f_data.get("success") else "❌ Error"
            cu = f_data.get("compiler_used", "gcc").upper()
            comp_lines.append(f"| `{f_name}` | **{st}** | {cu} |")

    diags = comp.get("translated_diagnostics", [])
    if diags:
        comp_lines.append("\n### Diagnósticos del Compilador Traducidos")
        comp_lines.append("| Archivo:Línea | Severidad | Mensaje Traducido | Sugerencia |")
        comp_lines.append("| :--- | :---: | :--- | :--- |")
        for d in diags:
            sug = d.get("suggestion", "")
            comp_lines.append(f"| `{d.get('file')}:{d.get('line')}` | **{d.get('severity')}** | {d.get('translated_message')} | {sug} |")
    elif comp.get("raw_stderr"):
        comp_lines.append("\n```text")
        comp_lines.append(comp["raw_stderr"][:1200])
        comp_lines.append("```")
    daed_path = rni_dir / "daedalus.md"
    daed_path.write_text("\n".join(comp_lines) + "\n", encoding="utf-8")
    generated["daedalus"] = daed_path

    # 2. Ripley (Reglas P1 / AST)
    ast_p1_findings = [f for f in ast_findings if not (f.get("rule_code") or "").startswith("SEC_") and not f.get("rule_name", "").startswith("[SEGURIDAD]")]
    rip_lines = ["## Observaciones de Calidad y Reglas P1 — Ripley"]
    if ast_p1_findings:
        rip_lines.append(f"\nSe detectaron **{len(ast_p1_findings)}** observación(es) en el código C:\n")
        rip_lines.append("| Regla | Ubicación | Severidad | Observación | Sugerencia |")
        rip_lines.append("| :--- | :--- | :---: | :--- | :--- |")
        for f in ast_p1_findings:
            rc = f.get("rule_code") or f.get("rule_id") or "P1"
            sug = f.get("suggestion", "")
            rip_lines.append(f"| `{rc}` | `{f.get('file')}:{f.get('line')}` | {f.get('severity')} | {f.get('message')} | {sug} |")
    else:
        rip_lines.append("\n✓ **Estado:** No se detectaron violaciones a las reglas de cátedra.")
    rip_path = rni_dir / "ripley.md"
    rip_path.write_text("\n".join(rip_lines) + "\n", encoding="utf-8")
    generated["ripley"] = rip_path

    # 3. Kaneda (Seguridad)
    sec_findings = [f for f in ast_findings if (f.get("rule_code") or "").startswith("SEC_") or f.get("rule_name", "").startswith("[SEGURIDAD]")]
    kan_lines = ["## Auditoría de Seguridad — Kaneda"]
    if sec_findings:
        kan_lines.append(f"\n⚠️ **Alerta:** Se detectaron **{len(sec_findings)}** llamadas o patrones de riesgo de seguridad:\n")
        kan_lines.append("| Regla | Archivo:Línea | Severidad | Detalle | Sugerencia |")
        kan_lines.append("| :--- | :--- | :---: | :--- | :--- |")
        for sf in sec_findings:
            kan_lines.append(f"| `{sf.get('rule_code')}` | `{sf.get('file')}:{sf.get('line')}` | **{sf.get('severity')}** | {sf.get('message')} | {sf.get('suggestion')} |")
    else:
        kan_lines.append("\n✓ **Estado:** Código libre de llamadas del sistema restringidas o intentos de evasión de sandbox.")
    kan_path = rni_dir / "kaneda.md"
    kan_path.write_text("\n".join(kan_lines) + "\n", encoding="utf-8")
    generated["kaneda"] = kan_path

    # 4. Spunkmeyer (Antipatrones Didácticos)
    spk_findings = [f for f in ast_p1_findings if "antipattern" in str(f.get("rule_id", "")).lower() or "feof" in str(f.get("message", "")).lower()]
    spk_lines = ["## Antipatrones Didácticos — Spunkmeyer"]
    if spk_findings:
        spk_lines.append(f"\nSe detectaron **{len(spk_findings)}** antipatrones didácticos:\n")
        for sf in spk_findings:
            spk_lines.append(f"- **`{sf.get('rule_id')}`** en `{sf.get('file')}:{sf.get('line')}`: {sf.get('message')}")
    else:
        spk_lines.append("\n✓ **Estado:** No se detectaron antipatrones pedagógicos conocidos.")
    spk_path = rni_dir / "spunkmeyer.md"
    spk_path.write_text("\n".join(spk_lines) + "\n", encoding="utf-8")
    generated["spunkmeyer"] = spk_path

    # 5. Tests (Casos de prueba y Sandbox)
    test_lines = ["## Pruebas Funcionales y Casos de Test — Sandbox"]
    if tests.get("total", 0) > 0 or cases:
        passed_cnt = tests.get("passed", sum(1 for c in cases if c.get("passed")))
        total_cnt = tests.get("total", len(cases))
        rate = (passed_cnt / total_cnt * 100) if total_cnt > 0 else 0
        test_lines.append(f"\n**Resultado general:** {passed_cnt} / {total_cnt} pruebas aprobadas ({rate:.1f}% de éxito).\n")
        test_lines.append("| Caso de Prueba | Estado | Código Retorno | Fuga Memoria | Diagnóstico |")
        test_lines.append("| :--- | :---: | :---: | :---: | :--- |")
        failed_cases = []
        for tc in cases:
            st = "✓ PASÓ" if tc.get("passed") else "❌ FALLÓ"
            ret = str(tc.get("return_code", 0))
            leak = "⚠️ SÍ (Leak)" if tc.get("memory_leak") else "✓ NO"
            err = tc.get("sanitizer_error", "") or ""
            err_summary = err.splitlines()[0] if err else ("Timeout" if tc.get("timed_out") else "OK")
            test_lines.append(f"| `{tc.get('name')}` | **{st}** | `{ret}` | {leak} | {err_summary} |")
            if not tc.get("passed"):
                failed_cases.append(tc)

        if failed_cases:
            test_lines.append("\n### 🔍 Detalle de Casos de Prueba Fallidos\n")
            for fc in failed_cases:
                test_lines.append(f"#### Caso: `{fc.get('name')}`")
                if fc.get("input_data"):
                    test_lines.append(f"- **Entrada (`stdin`):**\n```text\n{fc.get('input_data').strip()}\n```")
                if fc.get("expected_output"):
                    test_lines.append(f"- **Salida esperada:**\n```text\n{fc.get('expected_output').strip()}\n```")
                if fc.get("actual_output"):
                    test_lines.append(f"- **Salida obtenida:**\n```text\n{fc.get('actual_output').strip()}\n```")
                if fc.get("diff"):
                    test_lines.append(f"- **Diferencia (Diff):**\n```diff\n{fc.get('diff').strip()}\n```")
                if fc.get("sanitizer_error"):
                    test_lines.append(f"- **Error / Diagnóstico:** {fc.get('sanitizer_error')}\n")
    else:
        test_lines.append("\n*No se ejecutaron casos de prueba automatizados para esta entrega.*")
    test_path = rni_dir / "tests.md"
    test_path.write_text("\n".join(test_lines) + "\n", encoding="utf-8")
    generated["tests"] = test_path

    # 6. Valgrind (Auditoría de Memoria Dinámica / Heap)
    val_lines = ["## Auditoría de Memoria Dinámica — Valgrind"]
    if val.get("executed"):
        if val.get("clean"):
            val_lines.append("\n✓ **Estado:** Sin fugas de memoria ni accesos inválidos (0 bytes perdidos en 0 bloques).")
        else:
            val_lines.append("\n❌ **Estado:** Se detectaron problemas de gestión de memoria dinámica:")
            val_lines.append(f"- **Fuga definitivamente perdida (definitely lost):** `{val.get('definitely_lost_bytes', 0)}` bytes en `{val.get('definitely_lost_blocks', 0)}` bloque(s)")
            val_lines.append(f"- **Fuga indirectamente perdida (indirectly lost):** `{val.get('indirectly_lost_bytes', 0)}` bytes en `{val.get('indirectly_lost_blocks', 0)}` bloque(s)")
            val_lines.append(f"- **Fuga posiblemente perdida (possibly lost):** `{val.get('possibly_lost_bytes', 0)}` bytes en `{val.get('possibly_lost_blocks', 0)}` bloque(s)")
            val_lines.append(f"- **Memoria aún alcanzable (still reachable):** `{val.get('still_reachable_bytes', 0)}` bytes en `{val.get('still_reachable_blocks', 0)}` bloque(s)")
            val_lines.append(f"- **Total de errores de contexto (ERROR SUMMARY):** `{val.get('total_errors', 0)}`")

            errs = val.get("errors", [])
            if errs:
                val_lines.append("\n| Tipo de Error | Diagnóstico |")
                val_lines.append("| :--- | :--- |")
                for e in errs[:10]:
                    val_lines.append(f"| **{e.get('kind')}** | `{e.get('message')}` |")
    else:
        cases_leaks = [c for c in cases if c.get("memory_leak")]
        if cases_leaks:
            val_lines.append(f"\n❌ **Estado:** Se detectaron fugas de memoria en **{len(cases_leaks)}** caso(s) de prueba:")
            for cl in cases_leaks:
                val_lines.append(f"- Caso `{cl.get('name')}`: Fuga de memoria / Sanitizer error.")
        else:
            val_lines.append("\n✓ **Estado:** No se detectaron fugas de memoria durante las pruebas en sandbox.")
    val_path = rni_dir / "valgrind.md"
    val_path.write_text("\n".join(val_lines) + "\n", encoding="utf-8")
    generated["valgrind"] = val_path

    # 7. Gaff (Linter de Estilo y Formato)
    gaff_lines = ["## Linter de Estilo y Formato — Gaff"]
    if style_findings:
        gaff_lines.append(f"\n⚠️ Se detectaron **{len(style_findings)}** observación(es) de estilo arquitectónico:\n")
        gaff_lines.append("| Regla | Ubicación | Observación | Sugerencia | Autofix |")
        gaff_lines.append("| :--- | :--- | :--- | :--- | :---: |")
        for sf in style_findings:
            rc = sf.get("rule_code", "GAFF")
            loc = f"`{sf.get('file')}:{sf.get('line')}`"
            msg = sf.get("message", "")
            sug = sf.get("suggestion", "")
            auto = "✓ Sí" if sf.get("autofixable") else "No"
            gaff_lines.append(f"| `{rc}` | {loc} | {msg} | {sug} | {auto} |")
    else:
        gaff_lines.append("\n✓ **Estado:** Código conforme a las reglas de estilo de la cátedra (snake_case, sin tabs, líneas ≤ 80 caracteres).")
    gaff_path = rni_dir / "gaff.md"
    gaff_path.write_text("\n".join(gaff_lines) + "\n", encoding="utf-8")
    generated["gaff"] = gaff_path

    # 8. Similitud Winnowing (similarity.md) si está disponible
    sim_data = analysis.get("plagiarism") or analysis.get("similarity")
    if sim_data:
        sim_lines = ["## Auditoría de Similitud de Código — Plagio"]
        sim_score = sim_data.get("similarity_score", 0.0)
        sim_lines.append(f"\n**Índice de similitud estructural:** `{sim_score * 100:.1f}%`")
        if sim_data.get("matches"):
            sim_lines.append("\n| Archivo Comparado | Porcentaje Similitud |")
            sim_lines.append("| :--- | :---: |")
            for m in sim_data["matches"]:
                sim_lines.append(f"| `{m.get('target_file')}` | `{m.get('score', 0) * 100:.1f}%` |")
        sim_path = rni_dir / "similarity.md"
        sim_path.write_text("\n".join(sim_lines) + "\n", encoding="utf-8")
        generated["similarity"] = sim_path

    # 9. Preguntas de Defensa Oral (oral_questions.md) si están disponibles
    oral_qs = analysis.get("oral_questions", [])
    if oral_qs:
        oral_lines = ["## Preguntas Guía para Defensa Oral de Código"]
        oral_lines.append("\nPreguntas automáticas generadas para auditar la comprensión del estudiante:\n")
        for i, q in enumerate(oral_qs, 1):
            oral_lines.append(f"### Pregunta {i}: {q.get('pregunta', '')}")
            if q.get("linea"):
                oral_lines.append(f"- **Ubicación en código:** Línea `{q.get('linea')}`")
            if q.get("concepto"):
                oral_lines.append(f"- **Concepto evaluado:** {q.get('concepto')}")
            if q.get("respuesta_esperada"):
                oral_lines.append(f"- **Respuesta esperada:** {q.get('respuesta_esperada')}\n")
        oral_path = rni_dir / "oral_questions.md"
        oral_path.write_text("\n".join(oral_lines) + "\n", encoding="utf-8")
        generated["oral_questions"] = oral_path

    return generated


def generate_consolidated_report_from_rni(
    rni_dir: Path,
    exercise: str,
    student: str,
    metadata: RepoMetadata,
    template_dir: Path,
    output_file: Path,
    revision: Optional[str] = None,
    guide: Optional[Any] = None,
) -> str:
    """Consolida todos los informes Markdown generados por herramientas dentro de rNi en un único informe."""
    lines = []

    # 1. Header template
    header_file = template_dir / "header.md"
    if header_file.is_file():
        lines.append(header_file.read_text(encoding="utf-8", errors="replace").strip())
    else:
        rev_title = f" ({revision})" if revision else ""
        lines.append(f"# Informe de Corrección — {exercise}{rev_title}")

    # 2. Metadatos de Repositorio y Guía
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

    lines.append("\n## Análisis de Código C e Informes de Herramientas")

    # 3. Incorporar informes modulares desde rNi en orden pedagógico
    priority_order = [
        "resumen.md",
        "daedalus.md",
        "ripley.md",
        "tests.md",
        "valgrind.md",
        "gaff.md",
        "kaneda.md",
        "spunkmeyer.md",
        "diagramas.md",
        "similarity.md",
        "oral_questions.md",
    ]
    included_files = set()

    if rni_dir.is_dir():
        # Incluir herramientas en orden prioritario
        for p_name in priority_order:
            p_file = rni_dir / p_name
            if p_file.is_file():
                lines.append("\n" + p_file.read_text(encoding="utf-8", errors="replace").strip())
                included_files.add(p_file.name)

        # Incluir cualquier otra herramienta arbitraria presente en rNi/*.md
        for other_md in sorted(rni_dir.glob("*.md")):
            if other_md.name not in included_files and other_md.name not in ("informe.md", "informe_consolidado.md"):
                lines.append(f"\n## Herramienta: {other_md.stem.title()}")
                lines.append(other_md.read_text(encoding="utf-8", errors="replace").strip())

    # 4. Footer template
    footer_file = template_dir / "footer.md"
    if footer_file.is_file():
        lines.append("\n" + footer_file.read_text(encoding="utf-8", errors="replace").strip())

    report_content = "\n".join(lines) + "\n"
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(report_content, encoding="utf-8")
    return report_content


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
    """Genera los informes individuales por herramienta en rNi y el informe consolidado final."""
    student_dir = repo_path.parent if re.match(r"^r\d+(?:_f)?$", repo_path.name, re.IGNORECASE) else repo_path
    rev_str = revision or resolve_submission_revision(repo_path, student)
    m_num = re.search(r"\d+", rev_str)
    rev_num = m_num.group(0) if m_num else "1"

    rni_dir = student_dir / f"r{rev_num}i"

    # 1. Escribir informes individuales de cada herramienta en rNi/
    write_individual_tool_reports(rni_dir, analysis, metadata=metadata, guide=guide)

    # 2. Generar informe consolidado a partir de rNi/
    return generate_consolidated_report_from_rni(
        rni_dir=rni_dir,
        exercise=exercise,
        student=student,
        metadata=metadata,
        template_dir=template_dir,
        output_file=output_file,
        revision=rev_str,
        guide=guide,
    )


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
    val = analysis.get("valgrind", {})
    style = analysis.get("style_findings", [])

    lines.append(f"- **Compilación ({comp.get('compiler_used', 'GCC').upper()}):** {'✓ Exitosa' if comp.get('success') else '✖ Falló'}")
    lines.append(f"- **Reglas P1 / Calidad:** {len(ast)} observación(es) detectada(s)")
    lines.append(f"- **Estilo y Formato (Gaff):** {'✓ Conforme' if not style else f'⚠️ {len(style)} observación(es)'}")
    if val.get("executed"):
        val_lost = val.get("definitely_lost_bytes", 0)
        val_msg = "✓ Sin fugas (0 bytes perdidos)" if val.get("clean") else f"❌ Fuga detectada ({val_lost} B perdidos)"
        lines.append(f"- **Memoria Dinámica (Valgrind):** {val_msg}")
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
    for sf in style:
        if sf.get("suggestion"):
            issues.append(f"{sf.get('rule_code', 'GAFF')}: {sf['suggestion']}")
    if val.get("executed") and not val.get("clean"):
        issues.append("Liberar toda la memoria dinámica reservada con malloc/calloc usando free() antes de terminar.")
    for tc in tests.get("cases", []):
        if not tc.get("passed"):
            issues.append(f"Revisar caso `{tc.get('name')}`: verificar lógica o manejo de límites.")

    if issues:
        lines.append("\n### 🔧 Pasos sugeridos para la próxima entrega:")
        for idx, iss in enumerate(issues[:8], 1):
            lines.append(f"{idx}. {iss}")

    lines.append("\n---\n*Cátedra de Programación 1 · Evaluación automatizada con Dredd*")
    return "\n".join(lines) + "\n"

