"""Módulo de resolución de herramientas hermanas del ecosistema Cátedra P1."""

from __future__ import annotations

import importlib
import logging
from pathlib import Path
import shutil
import sys
from typing import Any, Callable, Optional

logger = logging.getLogger("dredd.ecosystem")


def resolve_sibling_tool(
    tool_name: str,
    module_path: str,
    symbol_name: str,
) -> Optional[Callable[..., Any]]:
    """Resuelve dinámicamente un símbolo o función de una herramienta hermana del ecosistema.

    Estrategia en orden:
    1. Import directo del entorno Python activo (`importlib.import_module`).
    2. Import local buscando en el monorepo hermano `../<tool_name>/src`.
    3. Fallback a `None` con log descriptivo.
    """
    # 1. Import directo si está instalado en el venv actual
    try:
        mod = importlib.import_module(module_path)
        func = getattr(mod, symbol_name, None)
        if func is not None:
            return func
    except ImportError:
        pass

    # 2. Búsqueda en monorepo hermano
    try:
        tools_root = Path(__file__).resolve().parents[3]
        sibling_src = tools_root / tool_name / "src"
        if sibling_src.is_dir() and str(sibling_src) not in sys.path:
            sys.path.insert(0, str(sibling_src))

        mod = importlib.import_module(module_path)
        func = getattr(mod, symbol_name, None)
        if func is not None:
            return func
    except Exception as e:
        logger.debug(f"No se pudo importar '{symbol_name}' desde '{module_path}' ({tool_name}): {e}")

    return None


def resolve_sibling_cli(tool_name: str) -> Optional[str]:
    """Resuelve la ruta ejecutable de un CLI hermano en PATH, venvs hermanos o ~/.local/bin."""
    # 1. En PATH
    bin_path = shutil.which(tool_name)
    if bin_path:
        return bin_path

    # 2. En .venv de la herramienta hermana en el monorepo
    tools_root = Path(__file__).resolve().parents[3]
    sibling_venv_bin = tools_root / tool_name / ".venv" / "bin" / tool_name
    if sibling_venv_bin.is_file():
        return str(sibling_venv_bin)

    # 3. En ~/.local/bin
    local_bin = Path.home() / ".local" / "bin" / tool_name
    if local_bin.is_file():
        return str(local_bin)

    return None
