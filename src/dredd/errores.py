"""Errores de datos como mensajes para el estudiante o el docente, no como tracebacks (N-ECO-05).

Un YAML mal formado, una ruta que no existe o un archivo que ya existe son
errores esperables de uso, no fallas del programa: la CLI tiene que decir qué
pasó y salir con 1. `TyperConErrores` los intercepta alrededor de la app raíz.
Con `P1_DEPURAR=1` se deja pasar la excepción para ver el traceback completo.
"""

from __future__ import annotations

import os
import sys

import typer
import yaml
from rich.console import Console
from rich.markup import escape

_err_console = Console(stderr=True)

ERRORES_DE_DATOS = (
    yaml.YAMLError,
    FileNotFoundError,
    NotADirectoryError,
    IsADirectoryError,
    FileExistsError,
    PermissionError,
    UnicodeDecodeError,
    ValueError,  # incluye pydantic.ValidationError
)


def describir_error(error: BaseException) -> str:
    """Mensaje en español para un error de datos."""
    ruta = getattr(error, "filename", None)
    if isinstance(error, yaml.YAMLError):
        marca = getattr(error, "problem_mark", None)
        problema = getattr(error, "problem", None) or str(error)
        donde = f" (línea {marca.line + 1}, columna {marca.column + 1})" if marca is not None else ""
        return f"el archivo no es un YAML válido: {problema}{donde}."
    if isinstance(error, FileExistsError):
        return f"ya existe {ruta}: elegí otra ruta."
    if isinstance(error, NotADirectoryError):
        return f"se esperaba un directorio y {ruta} no lo es."
    if isinstance(error, IsADirectoryError):
        return f"se esperaba un archivo y {ruta} es un directorio."
    if isinstance(error, FileNotFoundError):
        return f"no existe {ruta}." if ruta else str(error)
    if isinstance(error, PermissionError):
        return f"no hay permiso para acceder a {ruta}."
    if isinstance(error, UnicodeDecodeError):
        return "el archivo no está codificado en UTF-8."
    return str(error)


class TyperConErrores(typer.Typer):
    """App Typer que muestra los errores de datos como mensajes y sale con 1."""

    def __call__(self, *args, **kwargs):
        try:
            return super().__call__(*args, **kwargs)
        except ERRORES_DE_DATOS as error:
            if os.environ.get("P1_DEPURAR"):
                raise
            _err_console.print(f"[bold red]Error:[/bold red] {escape(describir_error(error))}")
            sys.exit(1)
