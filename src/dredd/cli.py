"""CLI principal de Dredd: Orquestador de evaluación masiva, autograding y feedback."""

from pathlib import Path
from typing import List, Optional
import typer
from rich.console import Console
from rich.table import Table

from dredd.core.git_ops import ensure_submission_repo, get_repo_metadata
from dredd.core.github_api import open_pr_in_browser, post_pr_comment
from dredd.core.moodle import export_grades_csv, unpack_moodle_zip
from dredd.core.plagiarism import PlagiarismDetector
from dredd.core.reporter import generate_student_report
from dredd.core.ripley_client import run_ripley_analysis

app = typer.Typer(
    name="dredd",
    help="Orquestador docente de evaluación masiva y gestión de entregas (GitHub Classroom + Moodle).",
    no_args_is_help=True,
)
moodle_app = typer.Typer(name="moodle", help="Gestión de canales Moodle (ingesta ZIP y planillas).", no_args_is_help=True)
app.add_typer(moodle_app, name="moodle")

console = Console()


@app.command("eval")
def cmd_eval(
    exercise: str = typer.Argument(..., help="Nombre de la actividad / ejercicio (ej. tp01, tp02)."),
    student: Optional[str] = typer.Argument(None, help="Nombre de usuario del estudiante (opcional si se usa --all)."),
    org: str = typer.Option("INGCOM-UNRN-P1", "--org", "-o", help="Organización de GitHub."),
    all_students: bool = typer.Option(False, "--all", "-a", help="Evaluar todos los estudiantes presentes en el workspace."),
    template_dir: Path = typer.Option(Path("informe"), "--template-dir", "-t", help="Directorio con header.md y footer.md."),
) -> None:
    """Clona/actualiza el repositorio, ejecuta el análisis con Ripley y genera el informe Markdown."""
    workspace_dir = Path.cwd()
    submissions_dir = workspace_dir / f"{exercise}-submissions"

    target_students = []
    if student:
        target_students.append(student)
    elif all_students:
        if not submissions_dir.is_dir():
            console.print(f"[bold red]No existe el directorio de entregas: {submissions_dir}[/bold red]")
            raise typer.Exit(code=1)
        target_students = [d.name for d in sorted(submissions_dir.iterdir()) if d.is_dir() and not d.name.startswith(".")]
    else:
        console.print("[bold red]Debe especificar un estudiante o usar --all.[/bold red]")
        raise typer.Exit(code=1)

    table = Table(title=f"Evaluación Dredd — {exercise}")
    table.add_column("Estudiante", style="cyan", justify="left")
    table.add_column("Compilación", justify="center")
    table.add_column("Tests", justify="center")
    table.add_column("Reglas P1 / AST", justify="center")
    table.add_column("Informe", style="green")

    for s_name in target_students:
        console.print(f"[bold]Procesando estudiante:[/bold] [cyan]{s_name}[/cyan]...")

        try:
            repo_path = ensure_submission_repo(org, exercise, s_name, workspace_dir)
        except Exception as e:
            console.print(f"  [red]Error al obtener repositorio:[/red] {e}")
            table.add_row(s_name, "[red]GIT ERROR[/red]", "—", "—", "No generado")
            continue

        meta = get_repo_metadata(repo_path)
        analysis = run_ripley_analysis(repo_path)

        report_file = workspace_dir / f"{s_name}.md"
        generate_student_report(
            exercise=exercise,
            student=s_name,
            repo_path=repo_path,
            metadata=meta,
            analysis=analysis,
            template_dir=template_dir,
            output_file=report_file,
        )

        comp_ok = analysis.get("compilation", {}).get("success", False)
        comp_str = "[green]OK[/green]" if comp_ok else "[red]FALLÓ[/red]"

        tests_info = analysis.get("tests", {})
        tests_str = f"{tests_info.get('passed', 0)}/{tests_info.get('total', 0)}" if tests_info.get("total", 0) > 0 else "N/A"

        ast_count = len(analysis.get("ast_findings", []))
        ast_str = f"[yellow]{ast_count} obs[/yellow]" if ast_count > 0 else "[green]0 obs[/green]"

        table.add_row(s_name, comp_str, tests_str, ast_str, report_file.name)

    console.print("\n")
    console.print(table)
    console.print("\n[dim]Para enviar los comentarios a los PRs correspondientes, ejecute: dredd comment <ejercicio> <estudiante>[/dim]\n")


@app.command("comment")
def cmd_comment(
    exercise: str = typer.Argument(..., help="Nombre de la actividad."),
    student: str = typer.Argument(..., help="Nombre de usuario del estudiante."),
    org: str = typer.Option("INGCOM-UNRN-P1", "--org", "-o", help="Organización de GitHub."),
    open_browser: bool = typer.Option(False, "--open", help="Abrir la vista de cambios del PR en el navegador."),
    pr_number: Optional[int] = typer.Option(None, "--pr", help="Número específico de PR (por defecto autodetecta el abierto)."),
) -> None:
    """Envía el informe Markdown generado como comentario en el Pull Request de GitHub."""
    report_file = Path.cwd() / f"{student}.md"
    if not report_file.exists():
        console.print(f"[bold red]No se encontró el informe '{report_file.name}'. Ejecute primero 'dredd eval'.[/bold red]")
        raise typer.Exit(code=1)

    console.print(f"Publicando feedback para [cyan]{student}[/cyan] en GitHub...")
    try:
        post_pr_comment(org, student, report_file, pr_number=pr_number)
        console.print("[bold green]✓ Comentario publicado con éxito en el Pull Request.[/bold green]")
        if open_browser:
            open_pr_in_browser(org, student, pr_number=pr_number)
    except Exception as e:
        console.print(f"[bold red]Error al publicar comentario:[/bold red] {e}")
        raise typer.Exit(code=1)


@app.command("plagiarism")
def cmd_plagiarism(
    exercise: str = typer.Argument(..., help="Nombre de la actividad a auditar."),
    threshold: float = typer.Option(0.60, "--threshold", "-th", help="Umbral de similitud mínima (0.0 a 1.0)."),
) -> None:
    """Calcula la matriz de similitud Winnowing entre todas las entregas descargadas."""
    submissions_dir = Path.cwd() / f"{exercise}-submissions"
    if not submissions_dir.is_dir():
        console.print(f"[bold red]Directorio inexistente: {submissions_dir}[/bold red]")
        raise typer.Exit(code=1)

    detector = PlagiarismDetector(threshold=threshold)
    matches = detector.analyze_submissions(submissions_dir)

    if not matches:
        console.print(f"\n[bold green]✓ No se detectaron pares con similitud superior al {threshold*100:.0f}%.[/bold green]\n")
        return

    table = Table(title=f"Auditoría de Similitud y Plagio — {exercise}")
    table.add_column("Estudiante A", style="cyan")
    table.add_column("Estudiante B", style="cyan")
    table.add_column("Similitud", justify="center", style="bold red")
    table.add_column("Huellas Compartidas", justify="right")

    for m in matches:
        table.add_row(
            m.student_a,
            m.student_b,
            f"{m.similarity_pct:.1f}%",
            f"{m.shared_fingerprints} / {m.total_a}",
        )

    console.print("\n")
    console.print(table)


@moodle_app.command("ingest")
def cmd_moodle_ingest(
    zip_file: Path = typer.Argument(..., help="Archivo ZIP descargado de Moodle con las entregas de la tarea."),
    exercise: str = typer.Option(..., "--exercise", "-e", help="Nombre del ejercicio o TP."),
) -> None:
    """Descomprime un archivo ZIP masivo de Moodle organizándolo en <ejercicio>-submissions/."""
    if not zip_file.is_file():
        console.print(f"[bold red]Archivo ZIP inexistente: {zip_file}[/bold red]")
        raise typer.Exit(code=1)

    students = unpack_moodle_zip(zip_file, exercise, Path.cwd())
    console.print(f"\n[bold green]✓ {len(students)} entregas extraídas con éxito en {exercise}-submissions/[/bold green]\n")


@moodle_app.command("export")
def cmd_moodle_export(
    exercise: str = typer.Option(..., "--exercise", "-e", help="Nombre del ejercicio o TP."),
    output: Path = typer.Option(Path("calificaciones.csv"), "--output", "-o", help="Archivo CSV de salida."),
) -> None:
    """Exporta las calificaciones a un archivo CSV compatible con Moodle."""
    submissions_dir = Path.cwd() / f"{exercise}-submissions"
    if not submissions_dir.is_dir():
        console.print(f"[bold red]Directorio inexistente: {submissions_dir}[/bold red]")
        raise typer.Exit(code=1)

    # Exportar planilla básica
    export_grades_csv(exercise, submissions_dir, output, grades_map={})
    console.print(f"\n[bold green]✓ Planilla generada en: {output}[/bold green]\n")


if __name__ == "__main__":
    app()
