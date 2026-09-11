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


def auditar_git_forensics(
    repo_path: Path,
    max_skew_seconds: int = 300,
    console: Optional[Console] = None,
) -> Dict[str, Any]:
    """Audita marcas de tiempo y commits artificiales en un repositorio Git."""
    from datetime import timezone, timedelta

    cons = console or Console()
    repo = Path(repo_path).resolve()
    git_bin = shutil.which("git")

    if not git_bin or not (repo / ".git").is_dir():
        cons.print(f"[bold red]Error:[/] '{repo}' no es un repositorio Git válido.")
        return {
            "es_repo_git": False,
            "total_commits": 0,
            "anomalias": [],
            "alertas": ["No es un repositorio Git válido."],
            "rebase_masivo_detectado": False,
            "alteraciones_fecha_detectadas": False,
            "riesgo": "DESCONOCIDO",
            "commits": [],
        }

    cmd = [
        git_bin,
        "-C",
        str(repo),
        "log",
        "--pretty=format:%H|%h|%aI|%cI|%an|%cn|%s",
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)

    if res.returncode != 0 or not res.stdout.strip():
        cons.print(f"[bold yellow]Aviso:[/] Repositorio '{repo.name}' sin commits registrados.")
        return {
            "es_repo_git": True,
            "total_commits": 0,
            "anomalias": [],
            "alertas": ["Repositorio sin commits registrados."],
            "rebase_masivo_detectado": False,
            "alteraciones_fecha_detectadas": False,
            "riesgo": "ALTO",
            "commits": [],
        }

    lineas = res.stdout.strip().splitlines()
    total_commits = len(lineas)
    commits_data: List[Dict[str, Any]] = []
    anomalias: List[Dict[str, Any]] = []
    alertas: List[str] = []

    for l in lineas:
        partes = l.split("|", 6)
        if len(partes) == 7:
            commits_data.append({
                "hash_full": partes[0],
                "hash": partes[1],
                "author_date_str": partes[2],
                "committer_date_str": partes[3],
                "author_name": partes[4],
                "committer_name": partes[5],
                "mensaje": partes[6],
            })

    # Analizar marcas temporales por commit
    ahora_utc = datetime.now(timezone.utc)
    fechas_autor: List[datetime] = []
    fechas_committer: List[datetime] = []

    for c in commits_data:
        c_anomalias: List[str] = []
        try:
            fa = datetime.fromisoformat(c["author_date_str"])
            if fa.tzinfo is None:
                fa = fa.replace(tzinfo=timezone.utc)
            fechas_autor.append(fa)
            c["dt_author"] = fa
        except Exception:
            fa = None
            c["dt_author"] = None

        try:
            fc = datetime.fromisoformat(c["committer_date_str"])
            if fc.tzinfo is None:
                fc = fc.replace(tzinfo=timezone.utc)
            fechas_committer.append(fc)
            c["dt_committer"] = fc
        except Exception:
            fc = None
            c["dt_committer"] = None

        # Verificacion de fecha futura
        if fa and fa > ahora_utc + timedelta(seconds=120):
            c_anomalias.append("Fecha de autor en el futuro")
            anomalias.append({
                "hash": c["hash"],
                "tipo": "fecha_futura_autor",
                "descripcion": f"Fecha de autor {c['author_date_str']} posterior a la hora actual",
            })

        if fc and fc > ahora_utc + timedelta(seconds=120):
            c_anomalias.append("Fecha de committer en el futuro")
            anomalias.append({
                "hash": c["hash"],
                "tipo": "fecha_futura_committer",
                "descripcion": f"Fecha de committer {c['committer_date_str']} posterior a la hora actual",
            })

        # Desfase entre autor y committer
        if fa and fc:
            skew = abs((fc - fa).total_seconds())
            c["skew_segundos"] = skew
            if skew > max_skew_seconds:
                minutos_skew = skew / 60.0
                c_anomalias.append(f"Desfase autor/committer ({minutos_skew:.1f}m)")
                anomalias.append({
                    "hash": c["hash"],
                    "tipo": "desfase_autor_committer",
                    "descripcion": f"Desfase temporal de {minutos_skew:.1f} minutos entre autor y committer",
                    "skew_segundos": skew,
                })
        else:
            c["skew_segundos"] = 0.0

        c["anomalias"] = c_anomalias

    # Analisis de inversion cronologica (en orden cronologico ascendente)
    commits_cronologicos = list(reversed(commits_data))
    for i in range(1, len(commits_cronologicos)):
        anterior = commits_cronologicos[i - 1]
        actual = commits_cronologicos[i]
        fa_ant = anterior.get("dt_author")
        fa_act = actual.get("dt_author")
        if fa_ant and fa_act and fa_act < (fa_ant - timedelta(seconds=30)):
            dif_min = (fa_ant - fa_act).total_seconds() / 60.0
            actual.get("anomalias", []).append("Inversión cronológica")
            anomalias.append({
                "hash": actual["hash"],
                "tipo": "inversion_cronologica",
                "descripcion": f"Commit {actual['hash']} fechado {dif_min:.1f} minutos antes de su commit base {anterior['hash']}",
            })

    # Deteccion de rebase masivo previo a entrega:
    # Muchos commits con committer dates concentrados en rango minimo (< 120s) pero author dates dispersos (> 1 hora)
    rebase_masivo_detectado = False
    if len(fechas_committer) >= 3:
        duracion_committer = (max(fechas_committer) - min(fechas_committer)).total_seconds()
        duracion_autor = (max(fechas_autor) - min(fechas_autor)).total_seconds()
        if duracion_committer <= 120 and duracion_autor > 3600:
            rebase_masivo_detectado = True
            alertas.append(
                f"Rebase masivo detectado: {len(fechas_committer)} commits re-aplicados en {duracion_committer:.0f}s "
                f"(rango de autor abarca {duracion_autor / 3600:.1f} horas)."
            )

    alteraciones_fecha_detectadas = any(
        a["tipo"] in ("fecha_futura_autor", "fecha_futura_committer", "desfase_autor_committer", "inversion_cronologica")
        for a in anomalias
    )
    if alteraciones_fecha_detectadas:
        alertas.append("Alteraciones o inconsistencias manuales en marcas de tiempo detectadas.")

    if rebase_masivo_detectado or any(a["tipo"].startswith("fecha_futura") for a in anomalias):
        riesgo = "ALTO"
    elif alteraciones_fecha_detectadas:
        riesgo = "MEDIO"
    else:
        riesgo = "BAJO"

    # Presentacion en consola
    tabla = Table(title=f"🔬 Forense Git de Commits: {repo.name}", border_style="magenta")
    tabla.add_column("Hash", style="cyan", justify="center")
    tabla.add_column("Fecha Autor", style="white")
    tabla.add_column("Fecha Committer", style="white")
    tabla.add_column("Desfase", justify="right")
    tabla.add_column("Anomalías Detectadas", style="yellow")

    for c in commits_data:
        anom_txt = ", ".join(c.get("anomalias", [])) or "[green]Normal[/green]"
        skew_val = c.get("skew_segundos", 0.0)
        skew_txt = f"{skew_val:.0f}s" if skew_val > 0 else "-"
        tabla.add_row(
            c["hash"],
            c["author_date_str"][:19],
            c["committer_date_str"][:19],
            skew_txt,
            anom_txt,
        )

    cons.print(tabla)

    resumen_tabla = Table(title="📋 Dictamen Forense", border_style="cyan")
    resumen_tabla.add_column("Métrica / Verificación", style="bold")
    resumen_tabla.add_column("Resultado")

    resumen_tabla.add_row("Total Commits", str(total_commits))
    resumen_tabla.add_row(
        "Alteración de Fechas",
        "[bold red]SÍ[/bold red]" if alteraciones_fecha_detectadas else "[green]NO[/green]",
    )
    resumen_tabla.add_row(
        "Rebase Masivo Previo",
        "[bold red]SÍ[/bold red]" if rebase_masivo_detectado else "[green]NO[/green]",
    )
    color_riesgo = "red" if riesgo == "ALTO" else ("yellow" if riesgo == "MEDIO" else "green")
    resumen_tabla.add_row("Nivel de Riesgo Forense", f"[bold {color_riesgo}]{riesgo}[/bold {color_riesgo}]")

    cons.print(resumen_tabla)

    if alertas:
        cons.print("[bold yellow]Observaciones forenses:[/bold yellow]")
        for alt in alertas:
            cons.print(f"  • {alt}")

    # Limpiar objetos datetime antes de serializar o retornar
    commits_limpios = []
    for c in commits_data:
        c_copy = dict(c)
        c_copy.pop("dt_author", None)
        c_copy.pop("dt_committer", None)
        commits_limpios.append(c_copy)

    return {
        "es_repo_git": True,
        "total_commits": total_commits,
        "anomalias": anomalias,
        "alertas": alertas,
        "rebase_masivo_detectado": rebase_masivo_detectado,
        "alteraciones_fecha_detectadas": alteraciones_fecha_detectadas,
        "riesgo": riesgo,
        "commits": commits_limpios,
    }
