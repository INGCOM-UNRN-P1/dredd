"""oral-exam-companion — Guía de preguntas para coloquios (nuevas.md §4.5).

Combina el historial Git del alumno con los hallazgos técnicos de ripley para
generar una guía Markdown de preguntas personalizadas, priorizadas por Bloom:

- **Comprensión**: sobre decisiones visibles en el código.
- **Análisis**: qué pasa con entradas límite / por qué falla un test.
- **Evaluación**: complejidad, gestión de memoria, alternativas.
- **Creación**: cómo extendería la solución.

El análisis técnico se delega en `run_ripley_analysis` (ripley o fallback AST
nativo de dredd); si el repo no tiene historial Git, la guía se genera igual
con las banderas disponibles.
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


MENSAJES_GENERICOS = re.compile(
    r"^(fix|fixes|cambios?|update|updates|wip|avances?|tp|prueba|test|final|v\d+)\b.*$",
    re.IGNORECASE,
)

LIMITE_COMMIT_GRANDE = 200  # insertions en un solo commit


@dataclass
class BanderasGit:
    commits: int = 0
    lineas_agregadas: int = 0
    ultimo_push: Optional[str] = None
    commits_grandes: int = 0          # > LIMITE_COMMIT_GRANDE líneas
    mensajes_genericos: int = 0
    bomba_final: bool = False         # >70% del código llegó en el último commit
    advertencias: List[str] = field(default_factory=list)


def analizar_historial(repo: Path) -> BanderasGit:
    """Extrae banderas pedagógicas del historial Git del alumno."""
    banderas = BanderasGit()
    if not (repo / ".git").exists():
        banderas.advertencias.append("el directorio no es un repositorio Git")
        return banderas

    def _git(argumentos: List[str]) -> str:
        try:
            proc = subprocess.run(["git", "-C", str(repo)] + argumentos,
                                  capture_output=True, text=True, timeout=15)
            return proc.stdout if proc.returncode == 0 else ""
        except (subprocess.TimeoutExpired, OSError):
            return ""

    log_numstat = _git(["log", "--numstat",
                            "--pretty=format:@@@%h|%ad|%s", "--date=short"])
    if not log_numstat.strip():
        banderas.advertencias.append("sin commits accesibles")
        return banderas

    inserts_por_commit: List[int] = []
    for bloque in log_numstat.split("@@@"):
        bloque = bloque.strip()
        if not bloque:
            continue
        encabezado, *filas = bloque.splitlines()
        partes = encabezado.split("|", 2)
        hash_, fecha, mensaje = (partes + ["", "", ""])[:3]
        banderas.commits += 1
        banderas.ultimo_push = fecha or banderas.ultimo_push

        agregadas = sum(int(f.split("\t")[0]) for f in filas
                        if f and f.split("\t")[0].isdigit())
        inserts_por_commit.append(agregadas)
        if agregadas > LIMITE_COMMIT_GRANDE:
            banderas.commits_grandes += 1
        if MENSAJES_GENERICOS.match(mensaje.strip()):
            banderas.mensajes_genericos += 1

    total = sum(inserts_por_commit)
    banderas.lineas_agregadas = total
    if inserts_por_commit and total > 0:
        ultima_proporcion = inserts_por_commit[-1] / max(total, 1)
        banderas.bomba_final = (
            len(inserts_por_commit) >= 3 and ultima_proporcion > 0.7
        )
    return banderas


# ---------------------------------------------------------------------------
# Generación de preguntas por bandera técnica
# ---------------------------------------------------------------------------

def _preguntas_de_reporte_ripley(reporte: Dict) -> List[dict]:
    """Convierte hallazgos de ripley en preguntas ordenadas por Bloom."""
    preguntas: List[dict] = []
    if not reporte:
        return preguntas   # sin análisis disponible: no inventar banderas
    comp = reporte.get("compilation", {})
    if not comp.get("success", False):
        preguntas.append({
            "nivel": "Comprensión",
            "pregunta": "Tu entrega no compila en el entorno de evaluación. "
                        "¿Qué diferencias hay entre tu máquina y el corrector?",
        })

    tests = reporte.get("tests", {})
    fallidos = tests.get("failed", 0)
    if fallidos:
        preguntas.append({
            "nivel": "Análisis",
            "pregunta": f"Tienen {fallidos} test(s) en rojo. Elegí uno y explicá, "
                        "paso a paso, qué recibe tu función y qué devolvería según el código.",
        })

    for f in reporte.get("ast_findings", []):
        regla = str(f.get("rule_id", "")).upper()
        msg = str(f.get("message", ""))

        if "LEAK" in regla or "malloc" in msg.lower() or "free" in msg.lower():
            preguntas.append({
                "nivel": "Evaluación",
                "pregunta": f"En `{f.get('file')}:{f.get('line')}` hay una fuga o manejo "
                            "dudoso de memoria. ¿Quién es el dueño de ese bloque y dónde "
                            "debería liberarse?",
            })
        elif "GLOBAL" in regla or "global" in msg.lower():
            preguntas.append({
                "nivel": "Análisis",
                "pregunta": "Usaste variables globales. ¿Cómo harías el estado explícito "
                            "por parámetros y qué ganaría tu módulo en pruebas unitarias?",
            })
        elif "RECURSION" in regla or "recursi" in msg.lower():
            preguntas.append({
                "nivel": "Creación",
                "pregunta": "¿Cómo convertirías esa recursión en iterativa y cuándo "
                            "convendría cada versión?",
            })
        elif f.get("severity") == "ERROR":
            preguntas.append({
                "nivel": "Comprensión",
                "pregunta": f"Expliqué la regla incumplida en línea {f.get('line')}: "
                            f"{msg[:120]} ¿Por qué la cátedra la considera importante?",
            })

    metricas = reporte.get("metrics", {})
    cc = metricas.get("cyclomatic_complexity_max") or metricas.get("cyclomatic_complexity")
    if isinstance(cc, (int, float)) and cc >= 10:
        preguntas.append({
            "nivel": "Evaluación",
            "pregunta": f"Tu función más compleja tiene complejidad ciclomática {cc:g}. "
                        "¿Qué ramas podrías extraer a funciones auxiliares?",
        })
    return preguntas


PREGUNTAS_POR_BANDERA_GIT = [
    ("bomba_final", "Análisis",
     "Casi todo tu código llegó en el último commit. Contame cómo lo fuiste "
     "probando antes de subirlo y qué te costó más."),
    ("commits_grandes", "Análisis",
     "Tenes commits con más de 200 líneas. ¿Cómo separarías ese cambio grande "
     "en pasos revisables?"),
    ("mensajes_genericos", "Recordar",
     "Varios commits dicen 'fix'/'cambios'. Si tuvieras que volver a este TP "
     "dentro de seis meses, ¿qué información te falta en esos mensajes?"),
]


def generar_guia(repo: Path, nombre_alumno: Optional[str] = None,
                 ejercicio: Optional[str] = None,
                 correr_ripley: bool = True) -> str:
    """Genera la guía oral completa en Markdown."""
    alumno = nombre_alumno or repo.name.replace("-", " ").title()

    from dredd.core.ripley_client import run_ripley_analysis

    banderas = analizar_historial(repo)
    reporte: Dict = {}
    if correr_ripley and any(repo.glob("**/*.c")):
        try:
            reporte = run_ripley_analysis(repo)
        except Exception:
            reporte = {}

    hoy = datetime.now().strftime("%Y-%m-%d")
    lineas: List[str] = [
        f"# Guía Oral — {alumno}" + (f" — {ejercicio}" if ejercicio else ""),
        "",
        f"_Generada por dredd oral-exam-companion · {hoy}_",
        "",
        "## Datos del alumno",
        "",
        f"- Commits: {banderas.commits} | Líneas agregadas: {banderas.lineas_agregadas}"
        + (f" | Último push: {banderas.ultimo_push}" if banderas.ultimo_push else ""),
    ]
    for advertencia in banderas.advertencias:
        lineas.append(f"- ⚠️ {advertencia}")

    lineas += ["", "## Banderas detectadas", ""]
    if banderas.bomba_final:
        lineas.append("- 🔴 Patrón **bomba final**: la mayoría del código llegó al final.")
    if banderas.commits_grandes:
        lineas.append(f"- 🟡 {banderas.commits_grandes} commit(s) con más de "
                      f"{LIMITE_COMMIT_GRANDE} líneas.")
    if banderas.mensajes_genericos:
        lineas.append(f"- 🟡 {banderas.mensajes_genericos} mensajes de commit genéricos.")

    errores_ripley = sum(
        1 for f in reporte.get("ast_findings", []) if f.get("severity") == "ERROR"
    )
    tests = reporte.get("tests", {})
    if tests.get("total"):
        lineas.append(f"- Tests: {tests.get('passed', 0)}/{tests.get('total')} en verde."
                      if not errores_ripley else
                      f"- Tests: {tests.get('passed', 0)}/{tests.get('total')} · "
                      f"{errores_ripley} error(es) estático(s).")
    if not any(l.startswith(("- 🔴", "- 🟡", "- Tests")) for l in lineas):
        lineas.append("- ✅ Sin banderas rojas; profundizar con preguntas de creación.")

    # Preguntas: primero las derivadas de ripley (sobre código real), luego git
    preguntas = _preguntas_de_reporte_ripley(reporte)
    for clave, nivel, texto in PREGUNTAS_POR_BANDERA_GIT:
        if getattr(banderas, clave):
            preguntas.append({"nivel": nivel, "pregunta": texto})

    lineas += ["", "## Preguntas sugeridas (ordenadas por prioridad)", ""]
    if preguntas:
        for i, p in enumerate(preguntas, start=1):
            lineas.append(f"{i}. [{p['nivel']}] {p['pregunta']}")
    else:
        lineas.append("_Sin señales llamativas: usar banco genérico de la cátedra._")

    lineas.append("")
    return "\n".join(lineas)
