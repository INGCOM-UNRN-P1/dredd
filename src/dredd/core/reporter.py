"""Ensamblador de informes Markdown modulares para feedback en PRs y archivo docente."""

from pathlib import Path
import re
from typing import Any, Dict, List, Optional
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


def find_student_report(
    workspace_dir: Path,
    exercise: Optional[str] = None,
    student: Optional[str] = None,
) -> Optional[Path]:
    """Busca el informe Markdown generado más reciente para el estudiante o dentro de un directorio de entrega."""
    if exercise is None and student is None:
        student_dir = workspace_dir
        if student_dir.is_dir():
            candidates = []
            for pat in [f"{student_dir.name}_r*.md", "informe_r*.md", f"*_{student_dir.name}_r*.md", "*.md"]:
                for f in sorted(student_dir.glob(pat)):
                    if f.is_file() and not f.name.startswith("."):
                        candidates.append(f)
            if candidates:
                candidates.sort(key=lambda p: (p.stat().st_mtime, p.name), reverse=True)
                return candidates[0]
        return None

    from dredd.core.git_ops import resolve_submissions_dir

    _, submissions_dir = resolve_submissions_dir(workspace_dir, exercise or "")
    student_dir = submissions_dir / (student or "")

    if student_dir.is_dir():
        candidates = []
        student_name = student or student_dir.name
        for pat in [f"{student_name}_r*.md", "informe_r*.md", f"*_{student_name}_r*.md", "*.md"]:
            for f in sorted(student_dir.glob(pat)):
                if f.is_file() and not f.name.startswith("."):
                    candidates.append(f)
        if candidates:
            candidates.sort(key=lambda p: (p.stat().st_mtime, p.name), reverse=True)
            return candidates[0]

    if student:
        root_cand = [
            workspace_dir / f"{student}.md",
            workspace_dir / f"{student}_r1.md",
        ]
        for c in root_cand:
            if c.is_file():
                return c

    return None


def is_submission_failed(
    student_dir: Path,
    exercise_slug: Optional[str] = None,
    workspace_dir: Optional[Path] = None,
) -> bool:
    """Determina si la entrega de un estudiante está desaprobada, falló en compilación/tests o requiere re-evaluación."""
    from dredd.core.db import DatabaseManager

    # 1. Chequear SQLite .metadata.db en la carpeta del estudiante o en la carpeta padre
    for db_cand in [student_dir / ".metadata.db", student_dir.parent / ".metadata.db"]:
        if db_cand.is_file():
            try:
                db = DatabaseManager(db_cand)
                latest_rev = db.get_latest_revision(student_dir.name)
                if latest_rev:
                    with db._get_connection() as conn:
                        cursor = conn.cursor()
                        cursor.execute(
                            "SELECT compilation_status, preliminary_grade FROM evaluations WHERE revision_id = ?",
                            (latest_rev["id"],),
                        )
                        row = cursor.fetchone()
                        if row:
                            comp = row["compilation_status"]
                            grade = row["preliminary_grade"]
                            # Si falló la compilación o la nota preliminar es < 6.0, falló
                            if comp != "OK" or (grade is not None and grade < 6.0):
                                return True
                            # Chequear tests si los hubo
                            cursor.execute(
                                "SELECT passed FROM test_results WHERE evaluation_id IN (SELECT id FROM evaluations WHERE revision_id = ?)",
                                (latest_rev["id"],),
                            )
                            tests = cursor.fetchall()
                            if tests and any(not t["passed"] for t in tests):
                                return True
                            return False
            except Exception:
                pass

    # 2. Chequear informe Markdown existente
    ws = workspace_dir or Path.cwd()
    rep = None
    if exercise_slug:
        rep = find_student_report(ws, exercise_slug, student_dir.name)
    if not rep:
        rep = find_student_report(student_dir)

    if not rep or not rep.is_file():
        # Sin informe previo -> Requiere evaluación
        return True

    try:
        content = rep.read_text(encoding="utf-8", errors="replace")
        failure_markers = [
            "FALLÓ",
            "Falló la compilación",
            "Error de compilación",
            "ENTREGA NO APROBADA",
            "REQUIERE REVISIÓN",
            "✗ FAIL",
            "❌",
        ]
        if any(marker in content for marker in failure_markers):
            return True
        if "ENTREGA APROBADA" in content or "✓ Exitosa" in content or "✓ **Estado:** Compilación exitosa" in content:
            return False
    except Exception:
        return True

    # 3. Chequear directorios modulares rNi (daedalus.md, tests.md)
    for rni in sorted(student_dir.glob("r*i"), reverse=True):
        daed = rni / "daedalus.md"
        if daed.is_file():
            try:
                d_txt = daed.read_text(encoding="utf-8", errors="replace")
                if "Falló la compilación" in d_txt or "❌" in d_txt:
                    return True
            except Exception:
                pass
        tests_md = rni / "tests.md"
        if tests_md.is_file():
            try:
                t_txt = tests_md.read_text(encoding="utf-8", errors="replace")
                if "Fallaron" in t_txt or "❌" in t_txt:
                    return True
            except Exception:
                pass
        break

    return False


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
    binary_findings = analysis.get("binary_findings", [])

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
    b_info = analysis.get("baseline_info", {})
    if b_info.get("has_baseline") and b_info.get("uncompleted"):
        uncompleted = b_info.get("uncompleted", [])
        completed = b_info.get("completed", [])
        res_lines.append(
            f"> ℹ️ **Filtro de plantilla (`_baseline`):** Se evaluaron **{len(completed)}** ejercicio(s) completado(s): {', '.join(f'`{e}`' for e in completed)}. "
            f"Se ignoraron **{len(uncompleted)}** ejercicio(s) sin modificar (idénticos a la plantilla original): {', '.join(f'`{e}`' for e in uncompleted)}.\n"
        )
    res_lines.append("| Archivo | Estado Compilación | Evaluación de Estilo | Valgrind (Fugas) | Observaciones Cátedra |")
    res_lines.append("| :--- | :---: | :---: | :---: | :--- |")
    if binary_findings:
        res_lines.append(
            f"| `[ARCHIVOS_BINARIOS]` | ❌ ERROR ({len(binary_findings)} filtrados) | 0.0/10 | — | Se detectaron binarios prohibidos (.o/.exe) en la entrega |"
        )
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

    # 0.5. Auditoría de Archivos Binarios Prohibidos (binarios.md)
    if binary_findings:
        bin_lines = [
            "## ⚠️ Archivos Binarios Prohibidos Filtrados\n",
            "> ❌ **ERROR DE ENTREGA:** Se detectaron archivos binarios precompilados o ejecutables en la entrega del estudiante. ",
            "> Para mantener la reproducibilidad académica y evitar la ejecución de código no compilado desde fuentes, estos archivos fueron **filtrados y descartados** de la evaluación.\n",
            "| Archivo Binario | Regla | Severidad | Detalle del Error | Sugerencia |",
            "| :--- | :---: | :---: | :--- | :--- |",
        ]
        for bf in binary_findings:
            bin_lines.append(
                f"| `{bf.get('file')}` | `{bf.get('rule_code', '0x000Fh')}` | **{bf.get('severity', 'ERROR')}** | {bf.get('message')} | {bf.get('suggestion')} |"
            )
        bin_lines.append(
            "\n**Acción Requerida:** Las entregas deben contener exclusivamente código fuente editable (`.c`, `.h`), archivos de configuración (`Makefile`) y documentación (`.md`, `.txt`). Ejecutá `make clean` antes de comprimir tu entrega y verificá tu archivo `.gitignore`."
        )
        bin_path = rni_dir / "binarios.md"
        bin_path.write_text("\n".join(bin_lines) + "\n", encoding="utf-8")
        generated["binarios"] = bin_path

    # 0.6. Enunciado y Consigna de la Actividad (enunciado.md)
    if guide and (getattr(guide, "enunciado", "") or any(getattr(e, "enunciado", "") for e in getattr(guide, "exercises", []))):
        enunc_lines = [
            f"## 📋 Consigna y Enunciado — {guide.nombre}\n",
        ]
        if getattr(guide, "enunciado_source", None):
            enunc_lines.append(f"> 📌 **Origen del enunciado:** `{guide.enunciado_source}`\n")
        if getattr(guide, "enunciado", ""):
            enunc_lines.append(guide.enunciado)
            enunc_lines.append("\n---\n")

        sub_enuncs = [e for e in getattr(guide, "exercises", []) if getattr(e, "enunciado", "")]
        if sub_enuncs:
            enunc_lines.append("### Requerimientos por Ejercicio\n")
            for e in sub_enuncs:
                enunc_lines.append(f"#### `{e.display_name}`\n")
                enunc_lines.append(e.enunciado)
                if getattr(e, "pistas", []):
                    enunc_lines.append("\n**Pistas didácticas:**")
                    for p in e.pistas:
                        enunc_lines.append(f"- {p}")
                enunc_lines.append("")

        enunc_path = rni_dir / "enunciado.md"
        enunc_path.write_text("\n".join(enunc_lines) + "\n", encoding="utf-8")
        generated["enunciado"] = enunc_path

    # 1. Daedalus (Compilación)
    is_project = comp.get("is_project") or comp.get("compiler_used") in ("make_proyecto", "make_project")
    if rni_dir.name.startswith("i_"):
        r_tag = rni_dir.name[2:]
    else:
        m_rev = re.search(r"\d+", rni_dir.name)
        r_tag = f"r{m_rev.group(0)}" if m_rev else "r1"

    if is_project:
        comp_lines = ["## Compilación — Makefile raíz del Proyecto"]
        if comp.get("success"):
            comp_lines.append("\n✓ **Estado:** Compilación exitosa ejecutando el Makefile en la raíz (`make`).")
        else:
            comp_lines.append("\n❌ **Estado:** Falló la compilación mediante el Makefile de la raíz.")
            if comp.get("raw_stderr"):
                comp_lines.append(f"\n```text\n{comp['raw_stderr'][:1200]}\n```")

        comp_lines.append(f"\n> 📄 **Salida completa:** registrada en `compilacion_{r_tag}.log`.")
        daed_path = rni_dir / "daedalus.md"
        daed_path.write_text("\n".join(comp_lines) + "\n", encoding="utf-8")
        generated["daedalus"] = daed_path
    else:
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

        comp_lines.append(f"\n> 📄 **Salida completa de compilación:** registrada en `compilacion_{r_tag}.log`.")

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
    spk_findings = analysis.get("spunkmeyer_findings")
    if spk_findings is None:
        spk_findings = [f for f in ast_p1_findings if "antipattern" in str(f.get("rule_id", "")).lower() or "feof" in str(f.get("message", "")).lower()]
    spk_lines = ["## Antipatrones Didácticos — Spunkmeyer"]
    if spk_findings:
        spk_lines.append(f"\nSe detectaron **{len(spk_findings)}** observación(es) de antipatrones didácticos:\n")
        spk_lines.append("| Regla | Ubicación | Antipatrón | Diagnóstico | Sugerencia |")
        spk_lines.append("| :--- | :--- | :--- | :--- | :--- |")
        for sf in spk_findings:
            rc = sf.get("rule_code") or sf.get("rule_id", "SPK")
            loc = f"`{sf.get('file')}:{sf.get('line')}`"
            name = sf.get("name") or sf.get("alias") or "Antipatrón"
            msg = sf.get("message", "")
            sug = sf.get("suggestion", "")
            spk_lines.append(f"| `{rc}` | {loc} | **{name}** | {msg} | {sug} |")

        has_details = any(sf.get("explanation") or sf.get("example_bad") or sf.get("code_line") for sf in spk_findings)
        if has_details:
            spk_lines.append("\n### 🔍 Detalle Pedagógico de Antipatrones\n")
            for sf in spk_findings:
                rc = sf.get("rule_code") or sf.get("rule_id", "SPK")
                name = sf.get("name") or sf.get("alias") or "Antipatrón"
                spk_lines.append(f"#### Regla `{rc}`: {name}")
                spk_lines.append(f"- **Ubicación:** `{sf.get('file')}:{sf.get('line')}`")
                if sf.get("code_line"):
                    spk_lines.append(f"```c\n{sf.get('code_line')}\n```")
                if sf.get("explanation"):
                    spk_lines.append(f"- **Explicación:** {sf.get('explanation')}")
                if sf.get("suggestion"):
                    spk_lines.append(f"- **Sugerencia:** {sf.get('suggestion')}")
                if sf.get("example_bad") and sf.get("example_good"):
                    spk_lines.append(f"- **Ejemplo incorrecto:**\n```c\n{sf.get('example_bad')}\n```")
                    spk_lines.append(f"- **Ejemplo recomendado:**\n```c\n{sf.get('example_good')}\n```")
                spk_lines.append("")
    else:
        spk_lines.append("\n✓ **Estado:** No se detectaron antipatrones pedagógicos conocidos.")
    spk_path = rni_dir / "spunkmeyer.md"
    spk_path.write_text("\n".join(spk_lines) + "\n", encoding="utf-8")
    generated["spunkmeyer"] = spk_path

    # 5. Tests (Casos de prueba y Sandbox)
    is_project_tests = tests.get("is_project") or comp.get("is_project")
    if is_project_tests:
        test_lines = ["## Pruebas del Proyecto — Makefile raíz (`make test`)"]
        if tests.get("cases"):
            tc = tests["cases"][0]
            if tc.get("passed"):
                test_lines.append("\n✓ **Estado:** Pruebas del proyecto aprobadas con éxito (`make test`).")
            else:
                test_lines.append("\n❌ **Estado:** Fallaron las pruebas del proyecto (`make test`).")
                err_msg = tc.get("sanitizer_error", "")
                if err_msg:
                    test_lines.append(f"\n```text\n{err_msg[:1200]}\n```")
        elif tests.get("has_test_target") is False:
            test_lines.append("\n*El Makefile raíz no define un target 'test' automatizado.*")
        else:
            test_lines.append("\n*No se ejecutaron casos de prueba automatizados para esta entrega.*")
        test_path = rni_dir / "tests.md"
        test_path.write_text("\n".join(test_lines) + "\n", encoding="utf-8")
        generated["tests"] = test_path
    elif tests.get("total", 0) > 0 or cases:
        passed_cnt = tests.get("passed", sum(1 for c in cases if c.get("passed")))
        total_cnt = tests.get("total", len(cases))
        rate = (passed_cnt / total_cnt * 100) if total_cnt > 0 else 0
        test_lines = ["## Pruebas Funcionales y Casos de Test — Sandbox"]
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
        test_path = rni_dir / "tests.md"
        test_path.write_text("\n".join(test_lines) + "\n", encoding="utf-8")
        generated["tests"] = test_path
    else:
        test_lines = ["## Pruebas Funcionales y Casos de Test — Sandbox"]
        test_lines.append("\n*No se ejecutaron casos de prueba automatizados para esta entrega.*")
        test_path = rni_dir / "tests.md"
        test_path.write_text("\n".join(test_lines) + "\n", encoding="utf-8")
        generated["tests"] = test_path
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
    analysis: Optional[Dict[str, Any]] = None,
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
    if getattr(metadata, "full_hash", None):
        lines.append(f"**Commit SHA:** `{metadata.full_hash}`")
    if getattr(metadata, "author", None):
        lines.append(f"**Autor:** `{metadata.author}`")
    if getattr(metadata, "commit_date", None):
        lines.append(f"**Fecha del commit:** `{metadata.commit_date}`")
    if getattr(metadata, "commit_message", None):
        lines.append(f"**Mensaje:** `{metadata.commit_message}`")
    lines.append(f"**Fecha de evaluación:** {metadata.date_str}")
    if revision:
        lines.append(f"**Versión revisada:** `{revision}`")

    if guide and getattr(guide, "exercises", None):
        lines.append("\n## Especificación de la Guía")
        lines.append(f"**Guía vinculada:** `{guide.nombre}`")
        if getattr(guide, "enunciado_source", None):
            lines.append(f"**Origen de consigna:** `{guide.enunciado_source}`")
        ejs_str = ", ".join(f"`{e.display_name}`" for e in guide.exercises)
        lines.append(f"**Ejercicios requeridos:** {ejs_str}")
        b_info = (analysis or {}).get("baseline_info", {})
        if b_info.get("has_baseline") and b_info.get("uncompleted"):
            uncompleted = b_info.get("uncompleted", [])
            completed = b_info.get("completed", [])
            lines.append(f"**Ejercicios completados:** {', '.join(f'`{e}`' for e in completed)}")
            lines.append(f"**Ejercicios sin modificar (_baseline):** {', '.join(f'`{e}`' for e in uncompleted)} *(ignorados)*")

    if metadata.files_list:
        lines.append("\n### Archivos contenidos")
        lines.append("```text")
        lines.append(metadata.files_list)
        lines.append("```")

    lines.append("\n## Análisis de Código C e Informes de Herramientas")

    # 3. Incorporar informes modulares desde rNi en orden pedagógico
    priority_order = [
        "resumen.md",
        "binarios.md",
        "enunciado.md",
        "daedalus.md",
        "ripley.md",
        "tests.md",
        "nostromo.md",
        "valgrind.md",
        "tetsuo.md",
        "hal.md",
        "gaff.md",
        "kaneda.md",
        "spunkmeyer.md",
        "brett.md",
        "bishop.md",
        "callahan.md",
        "motoko.md",
        "wierzbowski.md",
        "corbel.md",
        "zhora.md",
        "crowe.md",
        "dietrich.md",
        "drake.md",
        "vasquez.md",
        "vassili.md",
        "giger.md",
        "sebastian.md",
        "rachel.md",
        "ferro.md",
        "kane.md",
        "weyl.md",
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
                content = p_file.read_text(encoding="utf-8", errors="replace").strip()
                if content:
                    lines.append("\n" + content)
                included_files.add(p_file.name)

        # Incluir cualquier otra herramienta arbitraria presente en rNi/*.md
        for other_md in sorted(rni_dir.glob("*.md")):
            if other_md.name not in included_files and other_md.name not in ("informe.md", "informe_consolidado.md"):
                content = other_md.read_text(encoding="utf-8", errors="replace").strip()
                if content:
                    lines.append("\n" + content)
                    included_files.add(other_md.name)

    # 4. Footer template
    footer_file = template_dir / "footer.md"
    if footer_file.is_file():
        lines.append("\n" + footer_file.read_text(encoding="utf-8", errors="replace").strip())

    report_content = "\n".join(lines) + "\n"
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(report_content, encoding="utf-8")

    # Si existe log de compilación en rNi y aún no en output_file.parent, sincronizar
    m_num = re.search(r"\d+", revision or "")
    rev_tag = f"r{m_num.group(0)}" if m_num else "r1"
    src_log = rni_dir / f"compilacion_{rev_tag}.log"
    dst_log = output_file.parent / f"compilacion_{rev_tag}.log"
    if src_log.is_file() and not dst_log.exists():
        import shutil
        shutil.copy2(src_log, dst_log)

    return report_content


def build_full_compilation_log(
    analysis: Dict[str, Any],
    revision: str,
    student: Optional[str] = None,
    exercise: Optional[str] = None,
) -> str:
    """Construye el texto de la salida completa de la compilación."""
    comp = analysis.get("compilation", {})
    compiler_used = comp.get("compiler_used", "gcc").upper()
    success = comp.get("success", False)
    estado_str = "EXITOSA" if success else "FALLÓ"

    lines = [
        "=" * 80,
        "DREDD - SALIDA COMPLETA DE COMPILACIÓN",
        f"Actividad: {exercise or 'N/A'}",
        f"Estudiante: {student or 'N/A'}",
        f"Revisión: {revision}",
        f"Compilador / Modo: {compiler_used}",
        f"Estado general: {estado_str}",
        "=" * 80,
        "",
    ]

    files_comp = comp.get("files", {})
    if files_comp:
        lines.append("### COMPILACIÓN POR ARCHIVO FUENTE ###\n")
        for f_name, f_data in sorted(files_comp.items()):
            f_ok = f_data.get("success", False)
            f_st = "OK" if f_ok else "ERROR"
            cu = f_data.get("compiler_used", "gcc").upper()
            ret = f_data.get("returncode", 0 if f_ok else 1)
            lines.append(f"--- Archivo: {f_name} | Estado: {f_st} | Compilador: {cu} | Código Retorno: {ret} ---")
            cmd = f_data.get("command")
            if cmd:
                lines.append(f"$ {' '.join(str(c) for c in cmd)}")

            raw_out = f_data.get("full_output") or f_data.get("raw_stderr") or ""
            if not raw_out.strip() and f_ok:
                raw_out = "Compilación exitosa sin advertencias ni mensajes de error."
            lines.append(raw_out.strip())
            lines.append("")

    elif comp.get("full_output"):
        lines.append("### SALIDA COMPLETA DE COMPILACIÓN / BUILD ###\n")
        lines.append(comp["full_output"].strip())
        lines.append("")
    elif comp.get("raw_stderr"):
        lines.append("### SALIDA ESTÁNDAR DE ERROR (STDERR) ###\n")
        lines.append(comp["raw_stderr"].strip())
        lines.append("")
    else:
        if success:
            lines.append("Compilación exitosa sin advertencias ni mensajes de error.")
        else:
            lines.append("Falló la compilación pero no se registraron mensajes de salida.")
        lines.append("")

    diags = comp.get("translated_diagnostics", [])
    if diags:
        lines.append("-" * 80)
        lines.append("### DIAGNÓSTICOS DEL COMPILADOR TRADUCIDOS (DAEDALUS / ESPER) ###")
        lines.append("-" * 80)
        for idx, d in enumerate(diags, 1):
            f = d.get("file", "desconocido")
            line = d.get("line", 1)
            sev = d.get("severity", "ERROR")
            msg = d.get("translated_message", d.get("raw_message", ""))
            sug = d.get("suggestion", "")
            lines.append(f"[{idx}] {f}:{line} [{sev}] {msg}")
            if sug:
                lines.append(f"    Sugerencia: {sug}")
            if d.get("code_snippet"):
                lines.append(f"    Código: {d['code_snippet']}")
        lines.append("")

    lines.append("=" * 80)
    lines.append("FIN DE LA SALIDA DE COMPILACIÓN\n")
    return "\n".join(lines)


def save_compilation_log(
    output_dir: Path,
    analysis: Dict[str, Any],
    revision: str,
    student: Optional[str] = None,
    exercise: Optional[str] = None,
    output_stem: Optional[str] = None,
) -> List[Path]:
    """Guarda la salida completa de la compilación en output_dir con número de revisión."""
    output_dir.mkdir(parents=True, exist_ok=True)
    rev_raw = str(revision)
    if rev_raw.startswith("r") or len(rev_raw) >= 5 or not rev_raw.isdigit():
        rev_str = rev_raw
    else:
        rev_str = f"r{rev_raw}"
    log_content = build_full_compilation_log(
        analysis=analysis,
        revision=rev_str,
        student=student,
        exercise=exercise,
    )

    saved_paths: List[Path] = []

    # 1. Nombre canónico: compilacion_<revision>.log (ej: compilacion_r1.log o compilacion_a1b2c3d.log)
    canonical_file = output_dir / f"compilacion_{rev_str}.log"
    canonical_file.write_text(log_content, encoding="utf-8")
    saved_paths.append(canonical_file)

    # 2. Nombre con slug del estudiante si se dispone (ej: alvarez_juan_r1_compilacion.log)
    if student and str(student) != "None":
        clean_stud = Path(student).name
        student_file = output_dir / f"{clean_stud}_{rev_str}_compilacion.log"
        if student_file != canonical_file:
            student_file.write_text(log_content, encoding="utf-8")
            saved_paths.append(student_file)

    # 3. Si output_stem difiere (ej: informe_r1_compilacion.log)
    if output_stem:
        stem_clean = re.sub(r"_(?:r\d+|[0-9a-f]{6,40})$", "", output_stem, flags=re.IGNORECASE)
        stem_file = output_dir / f"{stem_clean}_{rev_str}_compilacion.log"
        if stem_file not in saved_paths:
            stem_file.write_text(log_content, encoding="utf-8")
            saved_paths.append(stem_file)

    return saved_paths


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
    intermediate_dir: Optional[Path] = None,
) -> str:
    """Genera los informes individuales por herramienta en rNi o i_<hash> y el informe consolidado final."""
    student_dir = repo_path.parent if re.match(r"^r\d+(?:_f)?$", repo_path.name, re.IGNORECASE) else repo_path
    rev_str = revision or resolve_submission_revision(repo_path, student)

    if intermediate_dir:
        rni_dir = intermediate_dir
        rev_tag = rev_str
    else:
        m_num = re.search(r"\d+", rev_str)
        rev_num = m_num.group(0) if m_num else "1"
        rev_tag = f"r{rev_num}"
        rni_dir = student_dir / f"r{rev_num}i"

    # 1. Guardar la salida completa de la compilación en la misma ubicación que el informe
    save_compilation_log(
        output_dir=output_file.parent,
        analysis=analysis,
        revision=rev_tag,
        student=student,
        exercise=exercise,
        output_stem=output_file.stem,
    )

    # También guardar una copia en el directorio modular rNi
    save_compilation_log(
        output_dir=rni_dir,
        analysis=analysis,
        revision=rev_tag,
        student=student,
        exercise=exercise,
    )

    # 2. Escribir informes individuales de cada herramienta en rNi/
    write_individual_tool_reports(rni_dir, analysis, metadata=metadata, guide=guide)

    # 3. Generar informe consolidado a partir de rNi/
    return generate_consolidated_report_from_rni(
        rni_dir=rni_dir,
        exercise=exercise,
        student=student,
        metadata=metadata,
        template_dir=template_dir,
        output_file=output_file,
        revision=rev_str,
        guide=guide,
        analysis=analysis,
    )


def generate_personalized_feedback_markdown(
    student_name: str,
    exercise_name: str,
    analysis: Dict[str, Any],
    metadata: Optional[RepoMetadata] = None,
    guide: Optional[Any] = None,
    revision: Optional[str] = None,
    template_path: Optional[Path] = None,
) -> str:
    """Genera una devolución personalizada en Markdown lista para adjuntar en Moodle / GitHub Classroom PR."""
    if template_path:
        from dredd.core.feedback_template import extract_context_from_analysis, load_and_render_feedback_template
        ctx = extract_context_from_analysis(analysis, student_name=student_name, exercise_name=exercise_name)
        if revision:
            ctx["revision"] = revision
        return load_and_render_feedback_template(template_path, ctx)

    comp = analysis.get("compilation", {})
    ast = analysis.get("ast_findings", [])
    tests = analysis.get("tests", {})
    binaries = analysis.get("binary_findings", [])

    passed = (
        comp.get("success", False)
        and (tests.get("failed", 0) == 0)
        and not any(f.get("severity") in ("ERROR", "FATAL") for f in ast)
        and not binaries
    )

    status_badge = "✅ **ENTREGA APROBADA**" if passed else "⚠️ **ENTREGA CON OBSERVACIONES / REQUIERE REVISIÓN**"
    if binaries:
        status_badge = "❌ **ENTREGA NO APROBADA (Archivos binarios prohibidos detectados)**"
    elif not comp.get("success", False):
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

    if binaries:
        lines.append(f"- **Archivos Binarios (.o, .a, .exe):** ❌ Se detectaron **{len(binaries)}** archivo(s) binario(s) prohibido(s) que fueron filtrados.")
    is_proj = comp.get("is_project") or comp.get("compiler_used") in ("make_proyecto", "make_project")
    if is_proj:
        lines.append(f"- **Compilación (Makefile raíz):** {'✓ Exitosa' if comp.get('success') else '✖ Falló'}")
        if tests.get("has_test_target"):
            t_ok = tests.get("failed", 0) == 0 and tests.get("passed", 0) > 0
            lines.append(f"- **Pruebas de proyecto (make test):** {'✓ Aprobadas' if t_ok else '✖ Fallaron'}")
    else:
        lines.append(f"- **Compilación ({comp.get('compiler_used', 'GCC').upper()}):** {'✓ Exitosa' if comp.get('success') else '✖ Falló'}")
    spk = analysis.get("spunkmeyer_findings", [])
    lines.append(f"- **Reglas P1 / Calidad:** {len(ast)} observación(es) detectada(s)")
    if spk:
        lines.append(f"- **Antipatrones didácticos (Spunkmeyer):** ⚠️ {len(spk)} observación(es) detectada(s)")
    else:
        lines.append("- **Antipatrones didácticos (Spunkmeyer):** ✓ Conforme (sin antipatrones detectados)")
    lines.append(f"- **Estilo y Formato (Gaff):** {'✓ Conforme' if not style else f'⚠️ {len(style)} observación(es)'}")
    if val.get("executed"):
        val_lost = val.get("definitely_lost_bytes", 0)
        val_msg = "✓ Sin fugas (0 bytes perdidos)" if val.get("clean") else f"❌ Fuga detectada ({val_lost} B perdidos)"
        lines.append(f"- **Memoria Dinámica (Valgrind):** {val_msg}")
    if not is_proj and tests.get("total", 0) > 0:
        lines.append(f"- **Casos de prueba:** {tests.get('passed', 0)}/{tests.get('total', 0)} aprobados")

    # Acciones concretas sugeridas
    issues = []
    if binaries:
        issues.append(f"Eliminar los {len(binaries)} archivos binarios precompilados (.o, .a, .exe) del repositorio usando `make clean` y `.gitignore`.")
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
    for sf in spk:
        if sf.get("suggestion"):
            issues.append(f"{sf.get('rule_code', 'SPK')}: {sf['suggestion']}")
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

