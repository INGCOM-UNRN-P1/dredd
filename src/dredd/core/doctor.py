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


def ejecutar_diagnostico_doctor(console: Optional[Console] = None) -> bool:
    """Muestra el diagnóstico completo de Dredd."""
    cons = console or Console()
    
    herramientas = [
        ("gcc", "Compilación de código C (fallback nativo)", True, "sudo apt install build-essential"),
        ("daedalus", "Compilador pedagógico oficial con flags cátedra P1", False, "pip install -e ../daedalus"),
        ("esper", "Explicador y traductor de diagnósticos GCC", False, "pip install -e ../esper"),
        ("valgrind", "Detección de fugas de memoria y memory errors", False, "sudo apt install valgrind"),
        ("nostromo", "Sandbox de aislamiento Bubblewrap y runner de tests", False, "pip install -e ../nostromo"),
        ("bwrap", "Sandbox de aislamiento Bubblewrap en el sistema", False, "sudo apt install bubblewrap"),
        ("git", "Operaciones de repositorio y auditoría de commits", True, "sudo apt install git"),
        ("gaff", "Linter canónico de reglas de estilo de cátedra", False, "pip install -e ../gaff"),
        ("spunkmeyer", "Detector de antipatrones didácticos C", False, "pip install -e ../spunkmeyer"),
        ("ripley", "Motor de análisis pedagógico P1 (satélite opcional)", False, "pip install -e ../ripley"),
        ("deckard", "Integración con guías y bancos de ejercicios", False, "pip install -e ../deckard"),
    ]
    
    tabla = Table(title="🏥 Diagnóstico del Entorno de Dredd (doctor)", border_style="cyan")
    tabla.add_column("Herramienta", style="bold white")
    tabla.add_column("Estado", justify="center")
    tabla.add_column("Versión / Ruta", style="dim")
    tabla.add_column("Propósito / Acción sugerida", style="yellow")
    
    todo_ok = True
    for cmd, desc, obligatorio, fix in herramientas:
        info = chequear_herramienta(cmd)
        if info["disponible"]:
            estado = "[bold green]✓ OK[/bold green]"
            detalles = f"{info['version']} ([cyan]{info['ruta']}[/cyan])"
            accion = desc
        else:
            if obligatorio:
                estado = "[bold red]✗ Faltante (Crítico)[/bold red]"
                todo_ok = False
            else:
                estado = "[yellow]! Opcional[/yellow]"
            detalles = "[dim]No encontrado en $PATH[/dim]"
            accion = f"{desc} ↳ Instalar: {fix}"
            
        tabla.add_row(cmd, estado, detalles, accion)
        
    cons.print(tabla)
    
    # Kernel checks
    k_caps = chequear_capacidades_kernel()
    if k_caps["bwrap_functional"]:
        cons.print("  [bold green]✓ Sandbox Bubblewrap:[/bold green] Kernel namespaces operativos para aislamiento seguro.")
    else:
        cons.print("  [yellow]! Sandbox Bubblewrap:[/yellow] Aislamiento limitado; se utilizará fallback de cuotas rlimit.")
        
    return todo_ok
