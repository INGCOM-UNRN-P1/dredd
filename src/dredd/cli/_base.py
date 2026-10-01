"""App de dredd, sus sub-apps y lo que comparten los comandos (N-DREDD-04)."""

import faulthandler
from typing import Any, Optional
import typer
from rich.console import Console

# Habilitar volcado de stacktrace nativo de Python ante fallos críticos (SIGSEGV, SIGABRT, SIGFPE, SIGBUS)
try:
    faulthandler.enable(all_threads=True)
except Exception:
    pass

from yutani.cli import TyperConErrores
from yutani.textos import traducir

# La app raíz muestra los errores de datos como mensajes (N-ECO-05).
# Ayuda y errores de Typer/Click en español, desde yutani (N-ECO-14).
traducir()
app = TyperConErrores(
    context_settings={"help_option_names": ["-h", "--help"]},
    name="dredd",
    help="Orquestador docente de evaluación masiva y gestión de entregas (GitHub Classroom + Moodle).",
    no_args_is_help=True,
)
moodle_app = typer.Typer(name="moodle", help="Gestión de canales Moodle (ingesta ZIP y planillas).", no_args_is_help=True)
app.add_typer(moodle_app, name="moodle")

github_app = typer.Typer(name="github", help="Comandos de integración con GitHub (clone, comment, pr-fix).", no_args_is_help=True)
app.add_typer(github_app, name="github")

config_app = typer.Typer(name="config", help="Gestión de configuración, entregas, guías y políticas de chequeo.", no_args_is_help=True)
app.add_typer(config_app, name="config")

evaluate_app = typer.Typer(name="evaluate", help="Evaluación docente, autograding y limpieza de entregas.", no_args_is_help=True)
app.add_typer(evaluate_app, name="evaluate")

console = Console()


def version_callback(value: bool) -> None:
    if value:
        from dredd import __version__
        console.print(f"dredd {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: Optional[bool] = typer.Option(
        None,
        "--version",
        "-v",
        help="Muestra la versión instalada de Dredd y finaliza.",
        callback=version_callback,
        is_eager=True,
    ),
) -> None:
    """Orquestador docente de evaluación masiva y gestión de entregas (GitHub Classroom + Moodle)."""
    pass


def _unwrap_cli_value(val: Any, fallback: Any = None) -> Any:
    """Extrae el valor por defecto si el argumento recibido es un OptionInfo o ArgumentInfo de Typer."""
    if hasattr(val, "default"):
        res = val.default
        if res is ...:
            return fallback
        return res
    return val
