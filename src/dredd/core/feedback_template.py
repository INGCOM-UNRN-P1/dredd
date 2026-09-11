"""Módulo de renderizado de plantillas de feedback enriquecidas con variables contextuales."""

from __future__ import annotations

from pathlib import Path
import re
from typing import Any, Dict, Optional

DEFAULT_FEEDBACK_TEMPLATE = """## Devolución Pedagógica — {student_name}
**Actividad:** `{exercise_name}`
**Estudiante:** `{student_id}`
**Estado:** {badge}
**Calificación estimada:** {score}/10

### 📋 Resumen de Pruebas
- **Total de pruebas:** {total_tests}
- **Pruebas aprobadas:** {passed_tests}
- **Fallos:** {failures}

### 🧠 Diagnóstico de Memoria
{memory_summary}

---
*Cátedra de Programación 1 · Evaluación automatizada con Dredd*
"""


def extract_context_from_analysis(
    analysis: Dict[str, Any],
    student_name: str = "estudiante",
    student_id: str = "",
    exercise_name: str = "actividad",
) -> Dict[str, Any]:
    """Extrae y formatea el contexto a partir del diccionario de análisis de Dredd/Ripley."""
    comp = analysis.get("compilation", {})
    ast = analysis.get("ast_findings", [])
    tests = analysis.get("tests", {})
    val = analysis.get("valgrind", {})
    binaries = analysis.get("binary_findings", [])

    total_tests = tests.get("total", 0)
    passed_tests = tests.get("passed", 0)
    failed_tests = tests.get("failed", 0)

    # Detalle de fallos
    failure_items = []
    for tc in tests.get("cases", []):
        if not tc.get("passed"):
            err_msg = tc.get("error_message") or tc.get("sanitizer_error") or "Salida incorrecta o timeout"
            failure_items.append(f"- `{tc.get('name', 'caso')}`: {err_msg}")
    failures_str = "\n".join(failure_items) if failure_items else "Ninguno detectado."

    # Resumen de memoria
    if val.get("executed"):
        if val.get("clean"):
            memory_summary = "✓ Sin fugas ni errores de memoria detectados (0 bytes perdidos)."
        else:
            lost = val.get("definitely_lost_bytes", 0)
            memory_summary = f"❌ Fuga o violación de memoria detectada: {lost} bytes definitivamente perdidos."
    else:
        memory_summary = "ℹ No se ejecutaron pruebas de Valgrind o sanitizers."

    # Veredicto y badge
    is_ok = (
        comp.get("success", False)
        and failed_tests == 0
        and not any(f.get("severity") in ("ERROR", "FATAL") for f in ast)
        and not binaries
    )
    if is_ok:
        badge = "✅ **ENTREGA APROBADA**"
        score = 10.0
    elif not comp.get("success", False):
        badge = "❌ **ENTREGA NO APROBADA (Error de compilación)**"
        score = 0.0
    elif binaries:
        badge = "❌ **ENTREGA NO APROBADA (Archivos binarios prohibidos)**"
        score = 1.0
    else:
        badge = "⚠️ **ENTREGA CON OBSERVACIONES**"
        score = max(2.0, round(10.0 * (passed_tests / max(1, total_tests)), 1))

    return {
        "student_id": student_id or student_name,
        "student_name": student_name,
        "exercise_name": exercise_name,
        "score": f"{score:.1f}",
        "total_tests": total_tests,
        "passed_tests": passed_tests,
        "failed_tests": failed_tests,
        "failures": failures_str,
        "memory_summary": memory_summary,
        "badge": badge,
    }


def render_feedback_template(template_str: str, context: Dict[str, Any]) -> str:
    """Renderiza una plantilla Markdown sustituyendo variables de tipo {variable} de forma tolerante."""
    result = template_str

    # Formateo mediante expresiones regulares para tolerar variables no presentes
    def replacer(match: re.Match[str]) -> str:
        key = match.group(1).strip()
        if key in context:
            return str(context[key])
        return match.group(0)  # Dejar intacto si no existe

    rendered = re.sub(r"\{([a-zA-Z0-9_]+)\}", replacer, result)
    return rendered


def load_and_render_feedback_template(
    template_path: Optional[Path],
    context: Dict[str, Any],
) -> str:
    """Carga una plantilla desde archivo o utiliza la plantilla por defecto si es None."""
    if template_path and template_path.is_file():
        template_str = template_path.read_text(encoding="utf-8")
    else:
        template_str = DEFAULT_FEEDBACK_TEMPLATE
    return render_feedback_template(template_str, context)
