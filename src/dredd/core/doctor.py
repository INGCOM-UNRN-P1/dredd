"""Diagnóstico de dependencias de sistema y capacidades de kernel para Dredd."""

from __future__ import annotations

import shutil
import subprocess
from typing import Dict, Any, List, Optional

from rich.console import Console
from rich.table import Table

from dredd.core.ecosystem import resolve_sibling_cli


def chequear_herramienta(comando: str, args_version: str = "--version") -> Dict[str, Any]:
    """Verifica si un comando está disponible en $PATH o en el ecosistema hermano y obtiene su versión."""
    path = resolve_sibling_cli(comando)
    if not path:
        return {"disponible": False, "version": None, "ruta": None}
    
    try:
        res = subprocess.run(
            [path, args_version],
            capture_output=True,
            text=True,
            timeout=3,
        )
        salida = (res.stdout or res.stderr).strip().splitlines()
        version = salida[0] if salida else "Detectada"
    except Exception:
        version = "Detectada"
        
    return {"disponible": True, "version": version, "ruta": path}


def chequear_capacidades_kernel() -> Dict[str, bool]:
    """Verifica soporte de namespaces y bubblewrap en el kernel Linux."""
    bwrap_path = shutil.which("bwrap")
    if not bwrap_path:
        return {"unshare_user": False, "bwrap_functional": False}
        
    try:
        res = subprocess.run(
            ["bwrap", "--ro-bind", "/", "/", "--dev", "/dev", "true"],
            capture_output=True,
            text=True,
            timeout=2,
        )
        bwrap_ok = (res.returncode == 0)
    except Exception:
        bwrap_ok = False
        
    return {"unshare_user": True, "bwrap_functional": bwrap_ok}


HERRAMIENTAS = [
    ("gcc", "Compilación de código C (fallback nativo)", True, "sudo apt install build-essential"),
    ("daedalus", "Compilador pedagógico oficial con flags cátedra P1", False, "uv tool install git+https://github.com/INGCOM-UNRN-P1/daedalus"),
    ("valgrind", "Detección de fugas de memoria y memory errors", False, "sudo apt install valgrind"),
    ("nostromo", "Sandbox de aislamiento Bubblewrap y runner de tests", False, "uv tool install git+https://github.com/INGCOM-UNRN-P1/nostromo"),
    ("bwrap", "Sandbox de aislamiento Bubblewrap en el sistema", False, "sudo apt install bubblewrap"),
    ("git", "Operaciones de repositorio y auditoría de commits", True, "sudo apt install git"),
    ("gaff", "Linter canónico de reglas de estilo de cátedra", False, "uv tool install git+https://github.com/INGCOM-UNRN-P1/gaff"),
    ("spunkmeyer", "Detector de antipatrones didácticos C", False, "uv tool install git+https://github.com/INGCOM-UNRN-P1/spunkmeyer"),
    ("ripley", "Motor de análisis pedagógico P1 (satélite opcional)", False, "uv tool install git+https://github.com/INGCOM-UNRN-P1/ripley"),
    ("deckard", "Integración con guías y bancos de ejercicios", False, "uv tool install git+https://github.com/INGCOM-UNRN/deckard"),
]


def diagnosticar() -> List[Dict[str, Any]]:
    """Estado de cada herramienta y del sandbox (sin imprimir nada)."""
    chequeos = []
    for cmd, desc, obligatorio, fix in HERRAMIENTAS:
        info = chequear_herramienta(cmd)
        chequeos.append({
            "nombre": cmd,
            "requerido": obligatorio,
            "ok": info["disponible"],
            "detalle": f"{info['version']} ({info['ruta']})" if info["disponible"] else "No encontrado en $PATH",
            "proposito": desc,
            "sugerencia": "" if info["disponible"] else fix,
        })
    capacidades = chequear_capacidades_kernel()
    chequeos.append({
        "nombre": "sandbox",
        "requerido": False,
        "ok": capacidades["bwrap_functional"],
        "detalle": "namespaces operativos para aislar las entregas" if capacidades["bwrap_functional"]
        else "sin bubblewrap funcional: las entregas no se ejecutan salvo DREDD_PERMITIR_SIN_SANDBOX=1",
        "proposito": "Aislamiento de las entregas (N-DREDD-02)",
        "sugerencia": "" if capacidades["bwrap_functional"] else "Instalá bubblewrap o nostromo",
    })
    return chequeos


def informe_json(chequeos: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Sobre JSON común de `doctor --json` (schema_version 1.0.0)."""
    from dredd import __version__

    return {
        "schema_version": "1.0.0",
        "herramienta": "dredd",
        "version": __version__,
        "ok": all(c["ok"] for c in chequeos if c["requerido"]),
        "chequeos": chequeos,
    }


def ejecutar_diagnostico_doctor(console: Optional[Console] = None) -> bool:
    """Muestra el diagnóstico completo de Dredd."""
    cons = console or Console()
    tabla = Table(title="🏥 Diagnóstico del Entorno de Dredd (doctor)", border_style="cyan")
    tabla.add_column("Herramienta", style="bold white")
    tabla.add_column("Estado", justify="center")
    tabla.add_column("Versión / Ruta", style="dim")
    tabla.add_column("Propósito / Acción sugerida", style="yellow")

    chequeos = diagnosticar()
    todo_ok = True
    for chequeo in chequeos:
        if chequeo["nombre"] == "sandbox":
            continue
        if chequeo["ok"]:
            estado = "[bold green]✓ OK[/bold green]"
            detalles = chequeo["detalle"]
            accion = chequeo["proposito"]
        else:
            if chequeo["requerido"]:
                estado = "[bold red]✗ Faltante (Crítico)[/bold red]"
                todo_ok = False
            else:
                estado = "[yellow]! Opcional[/yellow]"
            detalles = "[dim]No encontrado en $PATH[/dim]"
            accion = f"{chequeo['proposito']} ↳ Instalar: {chequeo['sugerencia']}"
        tabla.add_row(chequeo["nombre"], estado, detalles, accion)

    cons.print(tabla)

    sandbox = next(c for c in chequeos if c["nombre"] == "sandbox")
    if sandbox["ok"]:
        cons.print("  [bold green]✓ Sandbox Bubblewrap:[/bold green] Kernel namespaces operativos para aislamiento seguro.")
    else:
        cons.print("  [yellow]! Sandbox Bubblewrap:[/yellow] No funcional: las entregas no se ejecutan salvo que "
                   "exportes DREDD_PERMITIR_SIN_SANDBOX=1 (sin aislamiento). Instalá bubblewrap o nostromo.")

    return todo_ok
