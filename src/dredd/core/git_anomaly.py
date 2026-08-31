"""Detector de anomalías temporales y patrones de desarrollo en repositorios Git de alumnos."""

from __future__ import annotations

import subprocess
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
from rich.console import Console
from rich.table import Table


def auditar_historial_git(
    repo_path: Path,
    console: Optional[Console] = None,
) -> Dict[str, Any]:
    """Audita commits en un repositorio Git local para detectar anomalías."""
    cons = console or Console()
    repo = Path(repo_path).resolve()
    git_bin = shutil.which("git")

    if not git_bin or not (repo / ".git").is_dir():
        return {
            "es_repo_git": False,
            "total_commits": 0,
            "alertas": ["No es un repositorio Git válido."],
            "riesgo": "DESCONOCIDO",
        }

    # Obtener log de commits: hash|timestamp_iso|autor|mensaje
    cmd = [git_bin, "-C", str(repo), "log", "--pretty=format:%h|%aI|%an|%s"]
    res = subprocess.run(cmd, capture_output=True, text=True)

    if res.returncode != 0 or not res.stdout.strip():
        return {
            "es_repo_git": True,
            "total_commits": 0,
            "alertas": ["Repositorio sin commits registrados."],
            "riesgo": "ALTO",
        }

    lineas = res.stdout.strip().splitlines()
    total_commits = len(lineas)
    commits_data = []
    alertas: List[str] = []

    for l in lineas:
        partes = l.split("|", 3)
        if len(partes) == 4:
            commits_data.append({
                "hash": partes[0],
                "fecha": partes[1],
                "autor": partes[2],
                "mensaje": partes[3],
            })

    # Regla 1: Un solo commit masivo
    if total_commits == 1:
        alertas.append("Único commit inicial con todo el código final (sin desarrollo incremental).")

    # Regla 2: Commits concentrados en un lapso irreal (< 2 minutos para múltiples commits)
    if total_commits >= 3:
        try:
            fechas = [datetime.fromisoformat(c["fecha"]) for c in commits_data]
            fechas.sort()
            diff_segundos = (fechas[-1] - fechas[0]).total_seconds()
            if diff_segundos < 120:
                alertas.append(f"Todos los {total_commits} commits se crearon en menos de 2 minutos ({diff_segundos:.0f}s).")
        except Exception:
            pass

    riesgo = "ALTO" if alertas else "BAJO"

    tabla = Table(title=f"🕒 Auditoría Git de Desarrollo: {repo.name}", border_style="cyan")
    tabla.add_column("Total Commits", justify="center")
    tabla.add_column("Nivel de Riesgo", justify="center")
    tabla.add_column("Alertas de Proceso", style="yellow")

    riesgo_str = "[bold red]ALTO (Anomalía)[/bold red]" if alertas else "[bold green]BAJO (Normal)[/bold green]"
    alertas_str = "\n".join(f"• {a}" for a in alertas) if alertas else "[green]Desarrollo incremental normal.[/green]"
    tabla.add_row(str(total_commits), riesgo_str, alertas_str)

    cons.print(tabla)

    return {
        "es_repo_git": True,
        "total_commits": total_commits,
        "alertas": alertas,
        "riesgo": riesgo,
        "commits": commits_data,
    }
