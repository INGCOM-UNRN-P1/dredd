"""Comparador histórico inter-anual de similitud y plagio en Dredd."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Any, Optional
from rich.console import Console
from rich.table import Table

from dredd.core.plagiarism import PlagiarismDetector


def comparar_plagio_historico(
    dir_actual: Path,
    dir_historico: Path,
    umbral: float = 0.70,
    console: Optional[Console] = None,
) -> List[Dict[str, Any]]:
    """Compara entregas del período actual contra un corpus histórico de años anteriores."""
    cons = console or Console()
    detector = PlagiarismDetector(threshold=umbral)

    fuentes_actual = [p for p in Path(dir_actual).rglob("*.c") if not p.name.startswith(".")]
    fuentes_historico = [p for p in Path(dir_historico).rglob("*.c") if not p.name.startswith(".")]

    coincidencias: List[Dict[str, Any]] = []

    for f_act in fuentes_actual:
        for f_hist in fuentes_historico:
            sim = detector.calculate_similarity(f_act, f_hist)
            if sim >= umbral:
                coincidencias.append({
                    "actual": f_act,
                    "historico": f_hist,
                    "similitud": sim,
                })

    tabla = Table(title=f"🔎 Similitud Histórica Inter-Anual (Umbral: {umbral*100:.0f}%)", border_style="red" if coincidencias else "green")
    tabla.add_column("Entrega Actual", style="bold white")
    tabla.add_column("Entrega Histórica (Año previo)", style="cyan")
    tabla.add_column("Similitud", justify="right", style="bold yellow")

    for c in coincidencias:
        tabla.add_row(
            f"{c['actual'].parent.name}/{c['actual'].name}",
            f"{c['historico'].parent.name}/{c['historico'].name}",
            f"{c['similitud']*100:.1f}%",
        )

    if not coincidencias:
        tabla.add_row("[green]Sin coincidencias[/green]", "[green]Sin coincidencias[/green]", "0.0%")

    cons.print(tabla)
    return coincidencias
