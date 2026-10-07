"""Integración con GitHub y forense de repositorios: clone, comment, pr-fix, audit-git."""

from pathlib import Path
from typing import Optional
import typer
from rich.console import Console
from rich.table import Table
from dredd.core.git_ops import resolve_submissions_dir
from dredd.core.github_api import open_pr_in_browser, post_pr_comment
from dredd.core.reporter import find_student_report
from dredd.cli._base import _unwrap_cli_value, console  # noqa: F401


def cmd_github_clone(
    practica: str = typer.Argument(..., help="Nombre de la actividad / práctica (ej. TP0, tp01, etc.)."),
    directorio_destino: str = typer.Argument(..., help="Nombre del directorio destino para el estudiante (ej. TP0-Enehuen)."),
    repo_url: str = typer.Argument(..., help="URL del repositorio de GitHub a clonar (HTTPS o SSH)."),
) -> None:
    """Clona o actualiza el repositorio de una entrega de GitHub en <practica>/<directorio_destino>/repo."""
    from dredd.core.git_ops import clone_submission_repo, get_repo_metadata

    ws_dir = Path.cwd().resolve()
    exercise_slug, submissions_dir = resolve_submissions_dir(ws_dir, practica)

    console.print(f"Descargando entrega para [cyan]{directorio_destino}[/cyan] ({practica})...")
    try:
        repo_path, is_new, status_msg = clone_submission_repo(
            submissions_dir=submissions_dir,
            student_dir_name=directorio_destino,
            repo_url=repo_url,
        )
        meta = get_repo_metadata(repo_path)
        if is_new:
            console.print(f"[bold green]✓ Repositorio clonado exitosamente en:[/bold green] [cyan]{repo_path}[/cyan]")
        else:
            console.print(f"[bold green]✓ Repositorio actualizado ({status_msg}):[/bold green] [cyan]{repo_path}[/cyan]")
        console.print(f"  Rama: [yellow]{meta.branch}[/yellow] | Commit: [bold]{meta.revision}[/bold] ({meta.full_hash[:12]})")
        if meta.author:
            console.print(f"  Autor: [dim]{meta.author}[/dim] | Mensaje: [dim]{meta.commit_message}[/dim]")
    except Exception as e:
        console.print(f"[bold red]Error al clonar entrega de GitHub:[/bold red] {e}")
        raise typer.Exit(code=1) from e


def cmd_comment(
    exercise: str = typer.Argument(..., help="Nombre de la actividad."),
    student: str = typer.Argument(..., help="Nombre de usuario del estudiante."),
    org: str = typer.Option("INGCOM-UNRN-P1", "--org", "-o", help="Organización de GitHub."),
    open_browser: bool = typer.Option(False, "--open", help="Abrir la vista de cambios del PR en el navegador."),
    pr_number: Optional[int] = typer.Option(None, "--pr", help="Número específico de PR (por defecto autodetecta el abierto)."),
) -> None:
    """Envía el informe Markdown generado como comentario en el Pull Request de GitHub."""
    report_file = find_student_report(Path.cwd(), exercise, student)
    if not report_file or not report_file.exists():
        console.print(f"[bold red]No se encontró el informe para '{student}'. Ejecute primero 'dredd eval'.[/bold red]")
        raise typer.Exit(code=1)

    console.print(f"Publicando feedback para [cyan]{student}[/cyan] ({report_file.name}) en GitHub...")
    try:
        post_pr_comment(org, student, report_file, pr_number=pr_number)
        console.print("[bold green]✓ Comentario publicado con éxito en el Pull Request.[/bold green]")
        if open_browser:
            open_pr_in_browser(org, student, pr_number=pr_number)
    except Exception as e:
        console.print(f"[bold red]Error al publicar comentario:[/bold red] {e}")
        raise typer.Exit(code=1) from e


def cmd_pr_fix(
    practica: str = typer.Argument(..., help="Nombre de la actividad o práctica."),
    nombre_clonado: str = typer.Argument(..., help="Nombre con el que fue clonado el directorio del estudiante."),
    direccion: str = typer.Argument(..., help="Dirección o URL del repositorio en GitHub."),
    branch: str = typer.Option("correccion", "--branch", "-b", help="Nombre de la rama de corrección."),
    base: str = typer.Option("main", "--base", help="Rama base de destino para el Pull Request."),
) -> None:
    """Reconstruye o crea el Pull Request de corrección para un estudiante a partir de la práctica, nombre clonado y dirección remota."""
    from dredd.core.github_api import create_or_repair_pr, extract_repo_slug
    from dredd.core.git_ops import clone_submission_repo

    workspace_dir = Path.cwd()
    exercise_slug, submissions_dir = resolve_submissions_dir(workspace_dir, practica)
    target_dir = submissions_dir / nombre_clonado

    # Localizar el repositorio Git dentro de la carpeta del estudiante
    if (target_dir / "repo" / ".git").is_dir():
        repo_path = target_dir / "repo"
    elif (target_dir / ".git").is_dir():
        repo_path = target_dir
    else:
        console.print(f"Clonando entrega para [cyan]{nombre_clonado}[/cyan] desde '{direccion}'...")
        repo_path, _, _ = clone_submission_repo(
            submissions_dir=submissions_dir,
            student_dir_name=nombre_clonado,
            repo_url=direccion,
        )

    try:
        repo_target = extract_repo_slug(direccion)
        console.print(f"Reconstruyendo PR de corrección para [cyan]{nombre_clonado}[/cyan] ({repo_target})...")
        ok = create_or_repair_pr(
            student=nombre_clonado,
            repo_path=repo_path,
            branch_name=branch,
            base_branch=base,
            repo_target=repo_target,
            direccion=direccion,
        )
        if ok:
            console.print("[bold green]✓ Pull Request preparado o verificado con éxito en GitHub.[/bold green]")
        else:
            console.print("[bold yellow]⚠ El PR no pudo crearse automáticamente.[/bold yellow]")
    except Exception as e:
        console.print(f"[bold red]Error en pr-fix:[/bold red] {e}")
        raise typer.Exit(code=1) from e


def cmd_audit_git(
    repo: Path = typer.Argument(Path("."), exists=True, help="Ruta al repositorio de la entrega a auditar."),
) -> None:
    """Audita anomalías temporales y patrones de desarrollo en commits de Git."""
    from dredd.core.git_anomaly import auditar_historial_git
    auditar_historial_git(repo, console=console)


def cmd_git_forensics(
    repo: Path = typer.Argument(Path("."), exists=True, help="Ruta al repositorio de la entrega a auditar."),
    max_skew: int = typer.Option(300, "--max-skew", help="Tolerancia en segundos para desfase entre autor y committer."),
    json_output: bool = typer.Option(False, "--json", help="Exporta el resultado en formato JSON estándar."),
    fail_on_anomaly: bool = typer.Option(False, "--fail-on-anomaly", help="Finaliza con código de error si el riesgo forense es ALTO."),
) -> None:
    """Audita marcas de tiempo en Git para detectar alteraciones manuales o rebase masivo previo a entrega."""
    import json
    from dredd.core.git_anomaly import auditar_git_forensics
    c = Console(quiet=json_output)
    res = auditar_git_forensics(repo, max_skew_seconds=max_skew, console=c)
    if json_output:
        print(json.dumps(res, indent=2))
    if not res.get("es_repo_git"):
        raise typer.Exit(code=1)
    if fail_on_anomaly and res.get("riesgo") == "ALTO":
        raise typer.Exit(code=1)


def cmd_diff_submission(
    objetivo: str = typer.Argument(..., help="Ruta al directorio de la entrega o ruta a la primera versión R1."),
    segunda_version: Optional[str] = typer.Argument(None, help="Ruta a la segunda versión R2 o nombre de revisión (ej. 'r2')."),
    rev1_name: Optional[str] = typer.Option(None, "--r1", help="Nombre o subcarpeta de la primera revisión."),
    rev2_name: Optional[str] = typer.Option(None, "--r2", help="Nombre o subcarpeta de la segunda revisión."),
    entregas_dir: Path = typer.Option(Path("entregas"), "--entregas", "-e", help="Directorio base de entregas si se pasa nombre de alumno."),
    json_output: bool = typer.Option(False, "--json", help="Emitir reporte de diff en formato JSON."),
    output_md: Optional[Path] = typer.Option(None, "--md", "--output-md", "-o", help="Exportar reporte de diff a archivo Markdown."),
) -> None:
    """Compara dos versiones sucesivas de una entrega (R1 vs R2) mostrando cambios en código y funciones (QoL 3.15)."""
    import json
    from rich.panel import Panel
    from rich.syntax import Syntax
    from dredd.core.diff_submission import (
        comparar_revisiones_entrega,
        generar_markdown_diff_submission,
        resolver_carpetas_revision,
    )

    r1_arg = rev1_name or segunda_version
    r2_arg = rev2_name

    dir_r1, dir_r2, tag_r1, tag_r2 = resolver_carpetas_revision(
        objetivo,
        rev1_name=r1_arg,
        rev2_name=r2_arg,
        base_dir=entregas_dir,
    )

    diff = comparar_revisiones_entrega(dir_r1, dir_r2, label_r1=tag_r1, label_r2=tag_r2)

    if output_md:
        md_text = generar_markdown_diff_submission(diff)
        output_md.parent.mkdir(parents=True, exist_ok=True)
        output_md.write_text(md_text, encoding="utf-8")
        console.print(f"[bold green]✓ Reporte de reentrega generado en:[/bold green] [cyan]{output_md}[/cyan]")
        return

    if json_output:
        print(json.dumps(diff.to_dict(), indent=2, ensure_ascii=False))
        return

    console.print(Panel(
        f"[bold cyan]Dredd Diff Submission[/bold cyan] — Comparativa de Reentrega\n\n"
        f"• **Revisión 1:** [dim]{diff.origen_r1}[/dim] (`{diff.revision_1}`)\n"
        f"• **Revisión 2:** [dim]{diff.origen_r2}[/dim] (`{diff.revision_2}`)\n"
        f"• **Resumen:** [green]+{diff.total_agregadas}[/green] / [red]-{diff.total_eliminadas}[/red] líneas "
        f"({diff.archivos_modificados} modif, {diff.archivos_nuevos} nuevos, {diff.archivos_eliminados} elim)",
        title="[bold green]✓ Comparación de Versiones[/bold green]",
        border_style="cyan",
    ))

    if diff.funciones_alteradas:
        console.print(f"\n[bold yellow]⚡ Funciones C Afectadas:[/bold yellow] " + ", ".join(f"`{fn}()`" for fn in diff.funciones_alteradas))

    tabla = Table(title=f"Archivos Comparados ({len(diff.archivos)})", border_style="cyan")
    tabla.add_column("Archivo", style="bold white")
    tabla.add_column("Estado", justify="center")
    tabla.add_column("Líneas +", justify="right", style="green")
    tabla.add_column("Líneas -", justify="right", style="red")

    for a in diff.archivos:
        estado_style = {
            "MODIFICADO": "[yellow]MODIFICADO[/yellow]",
            "NUEVO": "[green]NUEVO[/green]",
            "ELIMINADO": "[red]ELIMINADO[/red]",
            "IDENTICO": "[dim]IDÉNTICO[/dim]",
        }.get(a.estado, a.estado)
        tabla.add_row(a.nombre, estado_style, f"+{a.lineas_agregadas}", f"-{a.lineas_eliminadas}")

    console.print(tabla)

    for a in diff.archivos:
        if a.diff_unified:
            console.print(Panel(
                Syntax(a.diff_unified, "diff", theme="monokai", line_numbers=True),
                title=f"Diff: {a.nombre}",
                border_style="dim",
            ))
