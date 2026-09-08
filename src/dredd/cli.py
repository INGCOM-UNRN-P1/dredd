"""CLI principal de Dredd: Orquestador de evaluación masiva, autograding y feedback."""

from pathlib import Path
from typing import Any, List, Optional
import typer
from rich.console import Console
from rich.table import Table

from dredd.core.git_ops import ensure_submission_repo, get_repo_metadata, resolve_submissions_dir
from dredd.core.github_api import open_pr_in_browser, post_pr_comment
from dredd.core.guide_integration import load_activity_guide
from dredd.core.moodle import export_grades_csv, unpack_moodle_zip
from dredd.core.plagiarism import PlagiarismDetector
from dredd.core.reporter import find_student_report, generate_student_report, resolve_submission_revision
from dredd.core.ripley_client import run_ripley_analysis

app = typer.Typer(
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


@app.command("init")
def cmd_init(
    path: Path = typer.Argument(Path("."), help="Directorio raíz donde inicializar el workspace de Dredd."),
    name: str = typer.Option("Cátedra Programación 1", "--name", "-n", help="Nombre del espacio de trabajo o materia."),
    zips_dir: str = typer.Option("zips", "--zips", "-z", help="Directorio para almacenar los archivos ZIP de Moodle."),
    entregas_dir: str = typer.Option("entregas", "--entregas", "-e", help="Directorio para las entregas descompactadas."),
    guias_dir: str = typer.Option("guias", "--guias", "-g", help="Directorio para las guías de Deckard."),
    force: bool = typer.Option(False, "--force", "-f", help="Sobrescribir dredd.yaml si ya existe."),
) -> None:
    """Inicializa un espacio de trabajo de Dredd con carpetas estructuradas y mapeo declarativo en dredd.yaml."""
    from dredd.core.config import init_workspace

    root, config_file = init_workspace(
        target_dir=path,
        name=name,
        zips_dir=zips_dir,
        submissions_dir=entregas_dir,
        guias_dir=guias_dir,
        force=force,
    )

    console.print(f"\n[bold green]✓ Espacio de trabajo de Dredd inicializado con éxito en:[/bold green] [cyan]{root}[/cyan]\n")
    console.print(f"  • [bold]Configuración central:[/bold] [cyan]{config_file}[/cyan]")
    console.print(f"  • [bold]Directorio de ZIPs Moodle:[/bold] [cyan]{root / zips_dir}/[/cyan]")
    console.print(f"  • [bold]Directorio de Entregas:[/bold] [cyan]{root / entregas_dir}/[/cyan]")
    console.print(f"  • [bold]Directorio de Guías Deckard:[/bold] [cyan]{root / guias_dir}/[/cyan]")
    console.print(f"  • [bold]Plantillas de informe:[/bold] [cyan]{root / 'plantillas'}/[/cyan]\n")
    console.print("[dim]Editá dredd.yaml para configurar los patrones de archivos ZIP y sus guías de Deckard asociadas.[/dim]\n")


def _unwrap_cli_value(val: Any, fallback: Any = None) -> Any:
    """Extrae el valor por defecto si el argumento recibido es un OptionInfo o ArgumentInfo de Typer."""
    if hasattr(val, "default"):
        res = val.default
        if res is ...:
            return fallback
        return res
    return val


def ejecutar_evaluacion(
    exercise: str,
    student: Optional[str] = None,
    org: str = "INGCOM-UNRN-P1",
    all_students: bool = False,
    template_dir: Path = Path("informe"),
    tipo_entrega: Optional[str] = None,
    dry_run: bool = False,
    failed_only: bool = False,
    workspace_dir: Optional[Path] = None,
    baseline: Optional[Path] = None,
) -> None:
    """Ejecuta el ciclo de evaluación sobre una o varias entregas de estudiantes."""
    from dredd.core.reporter import is_submission_failed

    exercise = _unwrap_cli_value(exercise, "")
    student = _unwrap_cli_value(student, None)
    org = _unwrap_cli_value(org, "INGCOM-UNRN-P1")
    all_students = bool(_unwrap_cli_value(all_students, False))
    template_dir = _unwrap_cli_value(template_dir, Path("informe"))
    if not isinstance(template_dir, Path):
        template_dir = Path(template_dir)
    tipo_entrega = _unwrap_cli_value(tipo_entrega, None)
    dry_run = bool(_unwrap_cli_value(dry_run, False))
    failed_only = bool(_unwrap_cli_value(failed_only, False))
    baseline = _unwrap_cli_value(baseline, None)
    if baseline is not None and not isinstance(baseline, Path):
        baseline = Path(baseline)
    ws_dir = (workspace_dir or Path.cwd()).resolve()

    exercise_slug, submissions_dir = resolve_submissions_dir(ws_dir, exercise)
    guide = load_activity_guide(submissions_dir, exercise_slug, ws_dir)

    # Determinar modo de construcción efectivo con precedencia: CLI override > dredd.yaml > Guía Deckard > Auto > Default
    from dredd.core.config import DreddConfig, load_dredd_config, normalize_delivery_mode
    cfg = load_dredd_config(submissions_dir) or load_dredd_config(ws_dir) or DreddConfig()
    effective_tipo = cfg.get_delivery_mode(
        activity_slug=exercise_slug,
        guide_mode=getattr(guide, "tipo_entrega", None),
        target_path=submissions_dir,
        cli_override=tipo_entrega,
    )

    target_students = []
    if student:
        target_students.append(student)
    elif all_students:
        if not submissions_dir.is_dir():
            console.print(f"[bold red]No existe el directorio de entregas: {submissions_dir}[/bold red]")
            raise typer.Exit(code=1)
        all_candidates = [
            d.name for d in sorted(submissions_dir.iterdir())
            if d.is_dir()
            and not d.name.startswith((".", "_", "i_"))
            and d.name not in ("guia", "guide", "templates", "informe", "informes", "baseline", "_baseline")
        ]
        if failed_only:
            target_students = [
                s for s in all_candidates
                if is_submission_failed(submissions_dir / s, exercise_slug, ws_dir)
            ]
            console.print(f"[bold cyan]🔍 Filtrado 'solo fallidas': {len(target_students)} de {len(all_candidates)} entrega(s) requieren re-evaluación.[/bold cyan]")
        else:
            target_students = all_candidates
    else:
        console.print("[bold red]Debe especificar un estudiante o usar --all.[/bold red]")
        raise typer.Exit(code=1)

    if dry_run and len(target_students) > 3:
        console.print(f"[bold yellow]⚡ Modo Dry Run activado: limitando evaluación a las primeras 3 entregas de {len(target_students)}.[/bold yellow]")
        target_students = target_students[:3]

    if not target_students:
        if failed_only:
            console.print(f"[bold green]✓ Todas las entregas en '{submissions_dir.name}' están aprobadas y sin fallos. Nada para re-evaluar.[/bold green]")
        else:
            console.print(f"[yellow]No se encontraron carpetas de estudiantes dentro de: {submissions_dir}[/yellow]")
        return

    if guide and guide.exercises:
        console.print(f"[bold green]✓ Guía Deckard conectada ('{guide.nombre}'): {len(guide.exercises)} ejercicio(s) ({', '.join(guide.get_exercise_ids())}) | Modo: {effective_tipo}[/bold green]")
    else:
        console.print(f"[bold blue]Modo de construcción activo: {effective_tipo}[/bold blue]")

    table = Table(title=f"Evaluación Dredd — {exercise_slug}")
    table.add_column("Estudiante", style="cyan", justify="left")
    table.add_column("Compilación", justify="center")
    table.add_column("Tests", justify="center")
    table.add_column("Reglas P1 / AST", justify="center")
    table.add_column("Informe", style="green")

    for s_name in target_students:
        console.print(f"[bold]Procesando estudiante:[/bold] [cyan]{s_name}[/cyan]...")

        try:
            repo_path = ensure_submission_repo(org, exercise_slug, s_name, ws_dir, submissions_dir=submissions_dir)
        except Exception as e:
            console.print(f"  [red]Error al obtener repositorio:[/red] {e}")
            table.add_row(s_name, "[red]ERROR[/red]", "—", "—", "No generado")
            continue

        repo_sub = repo_path / "repo"
        if repo_sub.is_dir():
            meta = get_repo_metadata(repo_sub)
            shorthash = meta.revision or meta.full_hash[:7] or "latest"
            all_revs = [(shorthash, repo_sub)]
            is_github_repo_mode = True
        elif (repo_path / ".git").is_dir():
            meta = get_repo_metadata(repo_path)
            shorthash = meta.revision or meta.full_hash[:7] or "latest"
            all_revs = [(shorthash, repo_path)]
            is_github_repo_mode = True
        else:
            from dredd.core.reformat import reformat_submission_to_rn_f, find_existing_revision_folders
            reformat_submission_to_rn_f(repo_path)
            all_revs = find_existing_revision_folders(repo_path)
            if not all_revs:
                all_revs = [(1, repo_path)]
            is_github_repo_mode = False

        for rev_identifier, r_path in all_revs:
            if is_github_repo_mode:
                shorthash = str(rev_identifier)
                rev_str = shorthash
                intermediate_dir = repo_path / f"i_{shorthash}"
                report_file = repo_path / f"{s_name}_{shorthash}.md"
            else:
                rev_str = f"r{rev_identifier}"
                intermediate_dir = repo_path / f"r{rev_identifier}i"
                report_file = repo_path / f"{s_name}_{rev_str}.md"

            meta = get_repo_metadata(r_path)
            analysis = run_ripley_analysis(
                r_path,
                guide=guide,
                activity_slug=exercise_slug,
                workspace_dir=ws_dir,
                tipo_entrega=effective_tipo,
                baseline_dir=baseline,
            )

            generate_student_report(
                exercise=exercise_slug,
                student=s_name,
                repo_path=r_path,
                metadata=meta,
                analysis=analysis,
                template_dir=template_dir,
                output_file=report_file,
                revision=rev_str,
                guide=guide,
                intermediate_dir=intermediate_dir,
            )

            comp_ok = analysis.get("compilation", {}).get("success", False)
            comp_str = "[green]OK[/green]" if comp_ok else "[red]FALLÓ[/red]"

            tests_info = analysis.get("tests", {})
            tests_str = f"{tests_info.get('passed', 0)}/{tests_info.get('total', 0)}" if tests_info.get("total", 0) > 0 else "N/A"

            ast_count = len(analysis.get("ast_findings", []))
            ast_str = f"[yellow]{ast_count} obs[/yellow]" if ast_count > 0 else "[green]0 obs[/green]"

            try:
                display_path = str(report_file.relative_to(ws_dir))
            except ValueError:
                display_path = str(report_file)

            student_label = f"{s_name} [{rev_str}]" if len(all_revs) > 1 else s_name
            table.add_row(student_label, comp_str, tests_str, ast_str, display_path)

    console.print("\n")
    console.print(table)
    console.print("\n[dim]Para enviar los comentarios a los PRs correspondientes, ejecute: dredd github comment <ejercicio> <estudiante>[/dim]\n")


@app.command("eval")
def cmd_eval(
    exercise: str = typer.Argument(..., help="Nombre de la actividad / ejercicio o ruta al directorio de entregas (ej. tp01, ./entrega-3_1238305/)."),
    student: Optional[str] = typer.Argument(None, help="Nombre de usuario del estudiante (opcional si se usa --all)."),
    org: str = typer.Option("INGCOM-UNRN-P1", "--org", "-o", help="Organización de GitHub."),
    all_students: bool = typer.Option(False, "--all", "-a", help="Evaluar todos los estudiantes presentes en el workspace."),
    template_dir: Path = typer.Option(Path("informe"), "--template-dir", "-t", help="Directorio con header.md y footer.md."),
    tipo_entrega: Optional[str] = typer.Option(
        None,
        "--tipo-entrega",
        "--build-mode",
        "-m",
        help="Tipo de entrega / modo de construcción ('archivos_individuales', 'makefiles_individuales' o 'proyecto'). Hace override a dredd.yaml y Deckard.",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Modo Dry Run: evalúa únicamente una muestra de hasta 3 estudiantes representativos antes del lote completo.",
    ),
    baseline: Optional[Path] = typer.Option(
        None,
        "--baseline",
        "-b",
        help="Directorio de línea base (_baseline) con las plantillas originales para omitir ejercicios sin completar.",
    ),
) -> None:
    """Clona/actualiza el repositorio o evalúa entregas locales, ejecuta el análisis con Ripley y genera el informe Markdown."""
    if exercise == "clean":
        ejecutar_limpieza_evaluaciones(
            exercise=student,
            student=None,
            all_students=all_students,
            dry_run=dry_run,
        )
        return

    ejecutar_evaluacion(
        exercise=exercise,
        student=student,
        org=org,
        all_students=all_students,
        template_dir=template_dir,
        tipo_entrega=tipo_entrega,
        dry_run=dry_run,
        baseline=baseline,
    )


def ejecutar_limpieza_evaluaciones(
    exercise: Optional[str] = None,
    student: Optional[str] = None,
    all_students: bool = False,
    dry_run: bool = False,
    rni_only: bool = False,
    reports_only: bool = False,
    verbose: bool = False,
) -> None:
    from dredd.core.eval_clean import limpiar_evaluaciones
    from dredd.core.git_ops import resolve_submissions_dir

    workspace_dir = Path.cwd()
    target_dir: Path

    if exercise:
        _, target_dir = resolve_submissions_dir(workspace_dir, exercise)
    else:
        cand = workspace_dir / "entregas"
        target_dir = cand if cand.is_dir() else workspace_dir

    rni_clean = not bool(reports_only)
    informes_clean = not bool(rni_only)

    res = limpiar_evaluaciones(
        base_dir=target_dir,
        student=student,
        dry_run=bool(dry_run),
        limpiar_rni=rni_clean,
        limpiar_informes=informes_clean,
    )

    rni_count = len(res["directorios_rni"])
    inf_count = len(res["informes"])
    est_count = res["estudiantes_afectados"]
    kb_liberados = res["bytes_liberados"] / 1024

    if dry_run:
        console.print(f"[bold yellow]⚡ Modo Simulación (Dry Run):[/bold yellow] Inspección de limpieza sobre [cyan]{target_dir}[/cyan]")
    else:
        console.print(f"[bold green]✓ Limpieza de evaluaciones completada en:[/bold green] [cyan]{target_dir}[/cyan]")

    if rni_count == 0 and inf_count == 0:
        console.print("[dim]No se encontraron evaluaciones previas (directorios rNi ni informes) para limpiar.[/dim]")
        return

    console.print(f"  • [bold]Directorios rNi {'a eliminar' if dry_run else 'eliminados'}:[/bold] [cyan]{rni_count}[/cyan]")
    console.print(f"  • [bold]Informes {'a eliminar' if dry_run else 'eliminados'}:[/bold] [cyan]{inf_count}[/cyan]")
    console.print(f"  • [bold]Estudiantes afectados:[/bold] [cyan]{est_count}[/cyan]")
    console.print(f"  • [bold]Espacio {'estimado' if dry_run else 'liberado'}:[/bold] [green]{kb_liberados:.1f} KB[/green]\n")

    if verbose:
        if res["directorios_rni"]:
            console.print("[bold underline]Directorios rNi:[/bold underline]")
            for d in res["directorios_rni"]:
                try:
                    rel = d.relative_to(workspace_dir)
                except ValueError:
                    rel = d
                console.print(f"  [red]✖ [DIR][/red] {rel}")

        if res["informes"]:
            console.print("\n[bold underline]Informes:[/bold underline]")
            for f in res["informes"]:
                try:
                    rel = f.relative_to(workspace_dir)
                except ValueError:
                    rel = f
                console.print(f"  [red]✖ [FILE][/red] {rel}")


@evaluate_app.command("clean")
@app.command("clean-eval", hidden=True)
def cmd_evaluate_clean(
    exercise: Optional[str] = typer.Argument(
        None,
        help="Nombre de la actividad o ruta al directorio de entregas (ej. tp01, ./entregas). Si no se indica, limpia en ./entregas o en el directorio actual.",
    ),
    student: Optional[str] = typer.Argument(
        None,
        help="Nombre de usuario del estudiante específico a limpiar (opcional; por defecto limpia todos).",
    ),
    all_students: bool = typer.Option(
        False,
        "--all",
        "-a",
        help="Limpiar todas las entregas encontradas.",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        "-n",
        help="Modo simulación: muestra qué carpetas rNi e informes se eliminarían sin borrar archivos.",
    ),
    rni_only: bool = typer.Option(
        False,
        "--rni-only",
        help="Limpiar exclusivamente los directorios rNi de herramientas, conservando los informes consolidados.",
    ),
    reports_only: bool = typer.Option(
        False,
        "--reports-only",
        help="Limpiar exclusivamente los archivos de informes Markdown/HTML/PDF, conservando los directorios rNi.",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Muestra cada archivo y carpeta eliminado en consola.",
    ),
) -> None:
    """Limpia las evaluaciones anteriores: elimina los directorios rNi y los informes generados."""
    ejecutar_limpieza_evaluaciones(
        exercise=exercise,
        student=student,
        all_students=all_students,
        dry_run=dry_run,
        rni_only=rni_only,
        reports_only=reports_only,
        verbose=verbose,
    )


@evaluate_app.command("run")
def cmd_evaluate_run(
    exercise: str = typer.Argument(..., help="Nombre de la actividad / ejercicio o ruta al directorio de entregas."),
    student: Optional[str] = typer.Argument(None, help="Nombre de usuario del estudiante (opcional si se usa --all)."),
    org: str = typer.Option("INGCOM-UNRN-P1", "--org", "-o", help="Organización de GitHub."),
    all_students: bool = typer.Option(False, "--all", "-a", help="Evaluar todos los estudiantes presentes en el workspace."),
    template_dir: Path = typer.Option(Path("informe"), "--template-dir", "-t", help="Directorio con header.md y footer.md."),
    tipo_entrega: Optional[str] = typer.Option(
        None,
        "--tipo-entrega",
        "--build-mode",
        "-m",
        help="Tipo de entrega / modo de construcción ('archivos_individuales', 'makefiles_individuales' o 'proyecto').",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Modo Dry Run: evalúa únicamente una muestra de hasta 3 estudiantes representativos antes del lote completo.",
    ),
) -> None:
    """Clona/actualiza el repositorio o evalúa entregas locales, ejecuta el análisis con Ripley y genera el informe Markdown."""
    ejecutar_evaluacion(
        exercise=exercise,
        student=student,
        org=org,
        all_students=all_students,
        template_dir=template_dir,
        tipo_entrega=tipo_entrega,
        dry_run=dry_run,
    )


@github_app.command("clone")
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
        raise typer.Exit(code=1)


@github_app.command("comment")
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
        raise typer.Exit(code=1)


@app.command("plagiarism")
def cmd_plagiarism(
    exercise: str = typer.Argument(..., help="Nombre de la actividad o directorio de entregas a auditar."),
    threshold: float = typer.Option(0.60, "--threshold", "-th", help="Umbral de similitud mínima (0.0 a 1.0)."),
    strip_template: Optional[Path] = typer.Option(None, "--strip-template",
        help="boiler-strip: plantilla/archivo(s) de cátedra a eliminar antes de calcular similitud."),
    html: Optional[Path] = typer.Option(None, "--html", help="Ruta del reporte HTML interactivo con matriz y diff lado a lado."),
) -> None:
    """Calcula la matriz de similitud Winnowing entre todas las entregas descargadas."""
    exercise_slug, submissions_dir = resolve_submissions_dir(Path.cwd(), exercise)
    if not submissions_dir.is_dir():
        console.print(f"[bold red]Directorio inexistente: {submissions_dir}[/bold red]")
        raise typer.Exit(code=1)

    if strip_template:
        console.print(f"[dim]boiler-strip activo contra: {strip_template}[/dim]")

    detector = PlagiarismDetector(threshold=threshold, plantilla=strip_template)
    matches = detector.analyze_submissions(submissions_dir)

    if not matches:
        console.print(f"\n[bold green]✓ No se detectaron pares con similitud superior al {threshold*100:.0f}%.[/bold green]\n")
        return

    table = Table(title=f"Auditoría de Similitud y Plagio — {exercise_slug}")
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
    console.print(table)

    if html:
        from dredd.core.plagiarism import generate_plagiarism_html_report
        generate_plagiarism_html_report(submissions_dir, matches, html)
        console.print(f"\n[bold green]✓ Reporte HTML interactivo generado en:[/bold green] [cyan]{html}[/cyan]\n")


@github_app.command("pr-fix")
def cmd_pr_fix(
    exercise: str = typer.Argument(..., help="Nombre de la actividad."),
    student: str = typer.Argument(..., help="Nombre de usuario del estudiante."),
    org: str = typer.Option("INGCOM-UNRN-P1", "--org", "-o", help="Organización de GitHub."),
    branch: str = typer.Option("correccion", "--branch", "-b", help="Nombre de la rama de corrección."),
) -> None:
    """Reconstruye o crea el Pull Request de corrección para un estudiante (reemplaza prfix.sh)."""
    from dredd.core.github_api import create_or_repair_pr

    workspace_dir = Path.cwd()
    exercise_slug, submissions_dir = resolve_submissions_dir(workspace_dir, exercise)
    try:
        repo_path = ensure_submission_repo(org, exercise_slug, student, workspace_dir, submissions_dir=submissions_dir)
        console.print(f"Reconstruyendo PR de corrección para [cyan]{student}[/cyan]...")
        ok = create_or_repair_pr(org, student, repo_path, branch_name=branch)
        if ok:
            console.print("[bold green]✓ Pull Request preparado o verificado con éxito en GitHub.[/bold green]")
        else:
            console.print("[bold yellow]⚠ El PR no pudo crearse automáticamente.[/bold yellow]")
    except Exception as e:
        console.print(f"[bold red]Error en pr-fix:[/bold red] {e}")
        raise typer.Exit(code=1)



@app.command("map")
def cmd_map(
    activity: str = typer.Argument(..., help="Nombre / slug de la actividad o directorio de entregas a mapear (ej. tp01, ./entrega-3_1238305/)."),
    exercises: Optional[List[str]] = typer.Option(None, "--exercise", "-e", help="Nombres de los ejercicios disponibles (ej. -e ej1 -e ej2)."),
    unmapped_only: bool = typer.Option(False, "--unmapped-only", "-u", help="Revisar únicamente archivos no vinculados."),
    auto: bool = typer.Option(False, "--auto", "-a", help="Aplicar coincidencias heurísticas obvias automáticamente."),
) -> None:
    """Mapeo interactivo y heurístico entre archivos C de estudiantes y especificaciones de la guía."""
    from dredd.core.mapping import InteractiveMapper

    workspace_dir = Path.cwd()
    exercise_slug, submissions_dir = resolve_submissions_dir(workspace_dir, activity)
    guide = load_activity_guide(submissions_dir, exercise_slug, workspace_dir)

    if exercises:
        avail = list(exercises)
    elif guide and guide.exercises:
        avail = guide.get_exercise_ids()
        console.print(f"[bold green]✓ Guía Deckard conectada ('{guide.nombre}'): {len(avail)} ejercicio(s) ({', '.join(avail)})[/bold green]")
    else:
        avail = ["ejercicio1", "ejercicio2", "ejercicio3"]

    mapper = InteractiveMapper(workspace_dir, exercise_slug, console=console, submissions_dir=submissions_dir)
    changes = mapper.run_interactive_session(avail, unmapped_only=unmapped_only, auto_apply=auto)
    console.print(f"[bold green]✓ Sesión finalizada: {changes} mapeo(s) actualizados.[/bold green]")


@moodle_app.command("ingest")
def cmd_moodle_ingest(
    zip_file: Path = typer.Argument(..., help="Archivo ZIP descargado de Moodle con las entregas de la tarea."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Solo simular la extracción sin escribir en disco."),
    force: bool = typer.Option(False, "--force", "-f", help="Re-ingestar sobrescribiendo revisiones previas."),
) -> None:
    """Descomprime, normaliza a UTF-8 y versiona (SHA-256) entregas masivas de Moodle."""
    from dredd.core.ingest import MoodleIngestor

    if not zip_file.is_file():
        console.print(f"[bold red]Archivo ZIP inexistente: {zip_file}[/bold red]")
        raise typer.Exit(code=1)

    workspace_dir = Path.cwd()
    if not (workspace_dir / "dredd.yaml").exists() and (zip_file.parent / "dredd.yaml").exists():
        workspace_dir = zip_file.parent

    ingestor = MoodleIngestor(workspace_dir)
    info, results = ingestor.process_zip(zip_file, dry_run=dry_run, force=force)

    new_revs = sum(1 for r in results if r.is_new_revision)
    console.print(f"\n[bold green]✓ Ingesta completada para '{info.activity_name}' ({info.activity_slug})[/bold green]")
    console.print(f"  · Estudiantes procesados: {len(results)}")
    console.print(f"  · Nuevas revisiones creadas: {new_revs}\n")

    if info.is_unknown_activity:
        console.print("[bold yellow]⚠ ADVERTENCIA: Práctica desconocida detectada[/bold yellow]")
        console.print(f"  • La actividad '{info.activity_name}' ({info.activity_slug}) no contaba con configuración previa en dredd.yaml.")
        console.print("  • Se generó un esqueleto de configuración en [cyan]dredd.yaml[/cyan].")
        console.print("  • [bold red]¡ATENCIÓN![/bold red] La configuración debe ser ajustada antes de evaluar:")
        console.print("      1. Asociá la guía Deckard en 'guia:' (ej. guias/<actividad>/guia.yaml).")
        console.print("      2. Verificá o ajustá el modo de construcción en 'mode:' ('archivos_individuales', 'makefiles_individuales' o 'proyecto').")
        console.print("      3. Ajustá las políticas de verificación en 'checks:' si corresponde.\n")


@app.command("export")
def cmd_export(
    activity: str = typer.Argument(..., help="Nombre / slug de la actividad a exportar."),
    csv_out: Optional[Path] = typer.Option(None, "--csv", "-c", help="Ruta del CSV de calificaciones Moodle."),
    zip_out: Optional[Path] = typer.Option(None, "--zip", "-z", help="Ruta del ZIP de retroalimentación Moodle."),
    dash_out: Optional[Path] = typer.Option(None, "--dashboard", "-d", help="Ruta del dashboard Markdown."),
) -> None:
    """Exporta calificaciones CSV, paquete ZIP de retroalimentación y dashboard consolidado de cohorte."""
    from dredd.core.exporter import MoodleExporter

    exporter = MoodleExporter(workspace_dir=Path.cwd())
    try:
        csv_file = exporter.export_grades_csv(activity, output_file=csv_out)
        zip_file = exporter.export_feedback_zip(activity, output_file=zip_out)
        dash_file = exporter.generate_dashboard(activity, output_file=dash_out)

        console.print(f"\n[bold green]✓ Exportación completada para '{activity}':[/bold green]")
        console.print(f"  · Libro de calificaciones: [cyan]{csv_file}[/cyan]")
        console.print(f"  · Paquete ZIP de retroalimentación: [cyan]{zip_file}[/cyan]")
        console.print(f"  · Dashboard de cohorte: [cyan]{dash_file}[/cyan]\n")
    except Exception as e:
        console.print(f"[bold red]Error durante la exportación:[/bold red] {e}")
        raise typer.Exit(code=1)


@app.command("export-report")
def cmd_export_report(
    source: Path = typer.Argument(..., help="Ruta al archivo Markdown (.md) del informe."),
    fmt: str = typer.Option("html", "--format", "-f", help="Formato de exportación: 'html' o 'pdf'."),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Ruta del archivo de salida."),
    title: str = typer.Option("Informe de Evaluación — Dredd", "--title", "-t", help="Título del informe."),
) -> None:
    """Convierte un informe Markdown a HTML autocontenido enriquecido o PDF (zero-dependencies)."""
    from dredd.core.report_export import export_report

    try:
        out_file = export_report(source, fmt=fmt, out_path=output, title=title)
        console.print(f"[bold green]✓ Informe exportado con éxito ({fmt.upper()}):[/bold green] [cyan]{out_file}[/cyan]")
    except Exception as e:
        console.print(f"[bold red]Error al exportar informe:[/bold red] {e}")
        raise typer.Exit(code=1)


@moodle_app.command("export")
def cmd_moodle_export(
    exercise: str = typer.Option(..., "--exercise", "-e", help="Nombre del ejercicio o TP."),
    output: Path = typer.Option(Path("calificaciones.csv"), "--output", "-o", help="Archivo CSV de salida."),
) -> None:
    """Exporta las calificaciones a un archivo CSV compatible con Moodle."""
    from dredd.core.exporter import MoodleExporter

    exporter = MoodleExporter(workspace_dir=Path.cwd())
    try:
        csv_file = exporter.export_grades_csv(exercise, output_file=output)
        console.print(f"\n[bold green]✓ Planilla generada en: {csv_file}[/bold green]\n")
    except Exception as e:
        console.print(f"[bold red]Error al exportar planilla Moodle:[/bold red] {e}")
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()


@app.command("fuzz-gen")
def fuzz_gen(
    modelo: Path = typer.Argument(..., exists=True, dir_okay=False,
                                  help="Solución modelo de la cátedra (.c)."),
    salida: Path = typer.Option(Path("casos"), "--salida", "-o",
                                help="Directorio destino de los pares caso_NN.in/.out."),
    spec: Optional[Path] = typer.Option(None, "--spec", help="spec.yaml opcional (tipo_entrada, semillas_extra, tamano_max)."),
    cantidad: int = typer.Option(12, "--cantidad", "-n", help="Máximo de testcases a generar."),
    segundos: int = typer.Option(15, "--segundos", help="Tiempo de fuzzing si hay clang/libFuzzer."),
    sin_libfuzzer: bool = typer.Option(False, "--sin-libfuzzer", help="Fuerza el modo determinista."),
):
    """fuzz-gen: endurece el banco generando casos límite contra la solución modelo.

    Combina semillas extremas deterministas (INT_MAX/INT_MIN, cadenas vacías,
    tamaños 0..N) con mutaciones y —si clang+libFuzzer están disponibles—
    fuzzing guiado por cobertura. Cada candidato se ejecuta contra el modelo
    para fijar la salida esperada; duplicados y crashes se reportan aparte.
    """
    from dredd.core.fuzz_gen import generar_testcases

    espec = None
    if spec:
        import yaml
        with open(spec, "r", encoding="utf-8") as f:
            espec = yaml.safe_load(f)

    console.print(f"[bold]fuzz-gen[/bold] sobre {modelo.name} → {salida}")
    try:
        resultado = generar_testcases(modelo, salida, spec=espec,
                                      cantidad_maxima=cantidad,
                                      usar_libfuzzer=not sin_libfuzzer,
                                      segundos_fuzz=segundos)
    except RuntimeError as e:
        console.print(f"[bold red]✗ {e}[/bold red]")
        raise typer.Exit(code=1)

    tabla = Table(title=f"Testcases generados (modo: {resultado.modo})")
    tabla.add_column("Entrada", style="cyan")
    tabla.add_column("Salida esperada", style="green")
    for in_p, out_p in resultado.generados:
        tabla.add_row(in_p.name, out_p.name)
    console.print(tabla)
    console.print(
        f"\n[green]✓ {len(resultado.generados)} casos generados[/green] · "
        f"{resultado.descartados_duplicados} duplicados descartados"
    )
    if resultado.crashes:
        console.print(f"[yellow]⚠ {len(resultado.crashes)} candidatos problemáticos:[/yellow]")
        for c in resultado.crashes[:5]:
            console.print(f"   · {c}")


@app.command("oral-guide")
def oral_guide(
    repo: Path = typer.Argument(..., exists=True, file_okay=False,
                                help="Repositorio del alumno (clonado en el workspace)."),
    alumno: Optional[str] = typer.Option(None, "--alumno", help="Nombre legible del alumno."),
    ejercicio: Optional[str] = typer.Option(None, "--ejercicio", help="TP/parcial asociado."),
    salida: Optional[Path] = typer.Option(None, "-o", "--salida", help="Archivo .md destino (por defecto, stdout)."),
    sin_ripley: bool = typer.Option(False, "--sin-ripley", help="No correr análisis técnico."),
) -> None:
    """oral-exam-companion: genera una guía de preguntas para coloquio/defensa."""
    from dredd.core.oral_guide import generar_guia

    guia = generar_guia(repo, nombre_alumno=alumno, ejercicio=ejercicio,
                        correr_ripley=not sin_ripley)
    if salida:
        salida.write_text(guia, encoding="utf-8")
        console.print(f"[green]✓ Guía oral generada[/green] → {salida}")
    else:
        console.print(guia)


@app.command("multiplex")
def cmd_multiplex(
    spec: Path = typer.Option(..., "--spec", "-s", exists=True, help="Ruta al archivo matriz.yaml."),
    students: Optional[Path] = typer.Option(None, "--students", exists=True, help="CSV con lista de alumnos."),
    salida: Path = typer.Option(Path("dist/multiplex"), "--salida", "-o", help="Directorio destino de la multiplexación."),
    pack: bool = typer.Option(True, "--pack/--no-pack", help="Generar paquetes .ripkg para cada variante."),
    starters: bool = typer.Option(True, "--starters/--no-starters", help="Generar starter repos por alumno."),
) -> None:
    """tp-multiplexer: Genera variantes combinatorias y asignación determinista por alumno."""
    import shutil
    import subprocess
    import sys

    # 1. Intentar ejecución vía CLI de deckard
    deckard_bin = shutil.which("deckard")
    if not deckard_bin:
        cand = Path(__file__).resolve().parent.parent.parent.parent / "deckard" / ".venv" / "bin" / "deckard"
        if cand.is_file():
            deckard_bin = str(cand)

    if deckard_bin:
        args = [deckard_bin, "multiplex", "--spec", str(spec), "-o", str(salida)]
        if students:
            args.extend(["--students", str(students)])
        if not pack:
            args.append("--no-pack")
        if not starters:
            args.append("--no-starters")
        proc = subprocess.run(args, capture_output=True, text=True)
        if proc.stdout:
            console.print(proc.stdout.rstrip())
        if proc.stderr:
            console.print(proc.stderr.rstrip())
        raise typer.Exit(code=proc.returncode)

    # 2. Fallback por import directo
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent / "deckard" / "src"))
        from deckard.core.multiplex import multiplexar_tp

        resultado = multiplexar_tp(
            matriz_path=spec,
            students_path=students,
            output_dir=salida,
            pack_ripkg=pack,
            generar_starters=starters,
        )
        console.print(f"[bold green]✓ Multiplexación completada para '{resultado.ejercicio}'[/bold green]")
        console.print(f"  • Total de variantes combinatorias: [cyan]{resultado.total_variantes}[/cyan]")
        console.print(f"  • Directorio de salida: [dim]{resultado.output_dir}[/dim]")
        if resultado.asignaciones:
            console.print(f"  • Estudiantes asignados: [green]{len(resultado.asignaciones)}[/green]")
    except Exception as e:
        console.print(f"[bold red]Error en multiplex:[/bold red] {e}")
        raise typer.Exit(code=1)


# ============================================================================
# Subcomandos de Gestión de Configuración (dredd config ...)
# ============================================================================


@config_app.command("show")
def cmd_config_show(
    entrega: Optional[str] = typer.Option(None, "--entrega", "-e", help="Mostrar detalle de una entrega específica."),
    workspace: Path = typer.Option(Path("."), "--workspace", "-w", help="Directorio raíz del workspace."),
) -> None:
    """Muestra la configuración activa de dredd.yaml, entregas mapeadas y políticas de chequeo."""
    from dredd.core.config import load_dredd_config

    cfg = load_dredd_config(workspace)
    if not cfg:
        console.print(f"[bold red]No se encontró dredd.yaml en {workspace.resolve()}.[/bold red]")
        console.print("[dim]Ejecutá 'dredd init' para crear uno nuevo.[/dim]")
        raise typer.Exit(code=1)

    console.print(f"\n[bold cyan]─── Espacio de Trabajo Dredd: {cfg.workspace.name} ───[/bold cyan]\n")
    console.print(f"  • [bold]Archivo de configuración:[/bold] [cyan]{cfg.config_path}[/cyan]")
    console.print(f"  • [bold]Directorio ZIPs:[/bold] [cyan]{cfg.workspace.zips_dir}/[/cyan]")
    console.print(f"  • [bold]Directorio Entregas:[/bold] [cyan]{cfg.workspace.submissions_dir}/[/cyan]")
    console.print(f"  • [bold]Directorio Guías:[/bold] [cyan]{cfg.workspace.guias_dir}/[/cyan]")
    console.print(f"  • [bold]Plantillas:[/bold] [cyan]{cfg.workspace.plantillas_dir}/[/cyan]\n")

    # Tabla de Chequeos Globales
    chk = cfg.checks
    t_chk = Table(title="Políticas Globales de Chequeo y Auditoría")
    t_chk.add_column("Herramienta", style="bold cyan")
    t_chk.add_column("Estado", justify="center")
    t_chk.add_column("Detalle / Parámetros")

    rip_status = "[green]ACTIVO[/green]" if chk.ripley_enabled else "[red]DESHABILITADO[/red]"
    rip_detail = f"Strict: {chk.ripley_strict}"
    if chk.ripley_disabled_rules:
        rip_detail += f" | Omitidas: {', '.join(chk.ripley_disabled_rules)}"
    if chk.ripley_rules:
        rip_detail += f" | Solo: {', '.join(chk.ripley_rules)}"
    t_chk.add_row("Ripley (Reglas P1 / AST)", rip_status, rip_detail)

    kan_status = "[green]ACTIVO[/green]" if chk.kaneda_enabled else "[red]DESHABILITADO[/red]"
    t_chk.add_row("Kaneda (Seguridad)", kan_status, f"Ban calls: {chk.ban_dangerous_calls} | Ban fork-bombs: {chk.ban_fork_bombs}")

    spk_status = "[green]ACTIVO[/green]" if chk.spunkmeyer_enabled else "[red]DESHABILITADO[/red]"
    t_chk.add_row("Spunkmeyer (Antipatrones)", spk_status, f"Ban feof: {chk.ban_feof_loop} | Ban gets: {chk.ban_gets}")

    gaff_status = "[green]ACTIVO[/green]" if chk.gaff_enabled else "[red]DESHABILITADO[/red]"
    t_chk.add_row("Gaff (Estilo Cátedra)", gaff_status, f"Snake_case: {chk.enforce_snake_case} | Var length: {chk.enforce_variable_length}")

    daed_status = "[green]ACTIVO[/green]"
    t_chk.add_row("Daedalus (Compilador)", daed_status, f"Compiler: {chk.daedalus_compiler.upper()} | Flags: {chk.compiler_flags}")

    t_chk.add_row("Sandbox (Aislamiento)", "[green]ACTIVO[/green]", f"RAM máx: {chk.sandbox_memory_mb} MB | Timeout: {chk.sandbox_timeout_seconds}s")
    console.print(t_chk)

    # Tabla de Entregas Mapeadas
    console.print("\n")
    t_map = Table(title="Entregas y Mapeos de Actividades")
    t_map.add_column("Entrega (Slug)", style="bold cyan")
    t_map.add_column("Patrón ZIP", style="yellow")
    t_map.add_column("Guía Deckard", style="green")
    t_map.add_column("Título")
    t_map.add_column("Overrides de Chequeo")

    for m in cfg.mapeos:
        overrides_str = ", ".join(f"{k}: {v}" for k, v in (m.checks or {}).items()) or "[dim]Hereda global[/dim]"
        t_map.add_row(m.entrega, m.zip_pattern, m.guia or "—", m.titulo or "—", overrides_str)

    console.print(t_map)
    console.print("")

    if entrega:
        eff = cfg.get_effective_checks(entrega)
        console.print(f"[bold cyan]Chequeos efectivos para '{entrega}':[/bold cyan]")
        console.print(f"  • Ripley: {eff.ripley_enabled} (Strict: {eff.ripley_strict}, Omitidas: {eff.ripley_disabled_rules or 'Ninguna'})")
        console.print(f"  • Seguridad Kaneda: {eff.kaneda_enabled}")
        console.print(f"  • Compilador: {eff.daedalus_compiler.upper()} ({eff.compiler_flags})")
        console.print(f"  • Sandbox: {eff.sandbox_memory_mb} MB RAM / {eff.sandbox_timeout_seconds}s\n")


@config_app.command("add-entrega")
def cmd_config_add_entrega(
    entrega: str = typer.Argument(..., help="Slug identificador de la entrega (ej. entrega_4, tp04)."),
    zip_pattern: str = typer.Option("*", "--zip", "-z", help="Patrón glob del archivo ZIP de Moodle (ej. '*entrega*4*.zip')."),
    guia: Optional[str] = typer.Option(None, "--guia", "-g", help="Ruta relativa a la guía Deckard (ej. 'guias/entrega_4/guia.yaml')."),
    titulo: str = typer.Option("", "--titulo", "-t", help="Título descriptivo de la actividad."),
    ripley_strict: Optional[bool] = typer.Option(None, "--ripley-strict/--no-ripley-strict", help="Modo estricto de Ripley para esta entrega."),
    disabled_rules: Optional[str] = typer.Option(None, "--disabled-rules", help="Códigos de reglas Ripley a omitir separados por coma (ej. '0x0009h,0x0004h')."),
    memory_mb: Optional[int] = typer.Option(None, "--memory-mb", help="Límite estricto de RAM en MB para el sandbox."),
    mode: Optional[str] = typer.Option(
        None,
        "--mode",
        "-m",
        help="Modo de construcción para esta entrega ('archivos_individuales', 'makefiles_individuales' o 'proyecto').",
    ),
    workspace: Path = typer.Option(Path("."), "--workspace", "-w", help="Directorio raíz del workspace."),
) -> None:
    """Agrega o actualiza una entrega en dredd.yaml con su patrón ZIP, guía Deckard, modo y chequeos específicos."""
    from dredd.core.config import load_dredd_config, MappingRule

    cfg = load_dredd_config(workspace)
    if not cfg:
        console.print(f"[bold red]No se encontró dredd.yaml en {workspace.resolve()}.[/bold red]")
        raise typer.Exit(code=1)

    checks_dict: Dict[str, Any] = {}
    if ripley_strict is not None:
        checks_dict.setdefault("ripley", {})["strict"] = ripley_strict
    if disabled_rules:
        rules_list = [r.strip() for r in disabled_rules.split(",") if r.strip()]
        checks_dict.setdefault("ripley", {})["disabled_rules"] = rules_list
    if memory_mb is not None:
        checks_dict.setdefault("sandbox", {})["max_memory_mb"] = memory_mb

    rule = MappingRule(
        zip_pattern=zip_pattern,
        entrega=entrega,
        guia=guia,
        titulo=titulo,
        checks=checks_dict if checks_dict else None,
        mode=mode,
    )
    cfg.add_or_update_mapping(rule)
    cfg.save()

    console.print(f"\n[bold green]✓ Entrega '{entrega}' guardada exitosamente en dredd.yaml:[/bold green]")
    console.print(f"  • [bold]Patrón ZIP:[/bold] [yellow]{zip_pattern}[/yellow]")
    console.print(f"  • [bold]Guía Deckard:[/bold] [cyan]{guia or 'No asignada'}[/cyan]")
    console.print(f"  • [bold]Modo de entrega:[/bold] [magenta]{mode or 'Auto / Heredado'}[/magenta]")
    console.print(f"  • [bold]Título:[/bold] {titulo or '—'}")
    if checks_dict:
        console.print(f"  • [bold]Overrides de chequeo:[/bold] {checks_dict}\n")


@config_app.command("remove-entrega")
def cmd_config_remove_entrega(
    entrega: str = typer.Argument(..., help="Slug identificador de la entrega a eliminar."),
    workspace: Path = typer.Option(Path("."), "--workspace", "-w", help="Directorio raíz del workspace."),
) -> None:
    """Elimina una entrega/actividad de la configuración dredd.yaml."""
    from dredd.core.config import load_dredd_config

    cfg = load_dredd_config(workspace)
    if not cfg:
        console.print(f"[bold red]No se encontró dredd.yaml en {workspace.resolve()}.[/bold red]")
        raise typer.Exit(code=1)

    ok = cfg.remove_mapping(entrega)
    if ok:
        cfg.save()
        console.print(f"\n[bold green]✓ Entrega '{entrega}' eliminada correctamente de dredd.yaml.[/bold green]\n")
    else:
        console.print(f"\n[bold yellow]⚠ No se encontró ninguna entrega con slug '{entrega}' en dredd.yaml.[/bold yellow]\n")


@config_app.command("set-check")
def cmd_config_set_check(
    tool: str = typer.Argument(..., help="Herramienta ('ripley', 'kaneda', 'spunkmeyer', 'gaff', 'daedalus', 'sandbox')."),
    setting: str = typer.Argument(..., help="Clave=valor a configurar (ej. 'strict=true', 'disabled_rules=0x0009h', 'max_memory_mb=128', 'compiler=gcc')."),
    entrega: Optional[str] = typer.Option(None, "--entrega", "-e", help="Slug de entrega específica (si se omite, aplica a nivel global)."),
    workspace: Path = typer.Option(Path("."), "--workspace", "-w", help="Directorio raíz del workspace."),
) -> None:
    """Configura parámetros de verificación de herramientas pedagógicas a nivel global o por entrega."""
    from dredd.core.config import load_dredd_config, ToolChecksConfig

    cfg = load_dredd_config(workspace)
    if not cfg:
        console.print(f"[bold red]No se encontró dredd.yaml en {workspace.resolve()}.[/bold red]")
        raise typer.Exit(code=1)

    if "=" not in setting:
        console.print("[bold red]Formato inválido. Use 'clave=valor' (ej. strict=true).[/bold red]")
        raise typer.Exit(code=1)

    key, raw_val = setting.split("=", 1)
    key = key.strip().lower()
    raw_val = raw_val.strip()

    if raw_val.lower() in ("true", "1", "yes", "si"):
        val: Any = True
    elif raw_val.lower() in ("false", "0", "no"):
        val = False
    elif raw_val.isdigit():
        val = int(raw_val)
    elif "," in raw_val:
        val = [v.strip() for v in raw_val.split(",") if v.strip()]
    else:
        val = raw_val

    tool_clean = tool.strip().lower()
    if entrega:
        rule = cfg.find_mapping_for_activity(entrega)
        if not rule:
            console.print(f"[bold red]No existe la entrega '{entrega}' en dredd.yaml.[/bold red]")
            raise typer.Exit(code=1)
        if not rule.checks:
            rule.checks = {}
        if tool_clean not in rule.checks or not isinstance(rule.checks[tool_clean], dict):
            rule.checks[tool_clean] = {}
        rule.checks[tool_clean][key] = val
        cfg.save()
        console.print(f"\n[bold green]✓ Chequeo '{tool_clean}.{key} = {val}' configurado para la entrega '{entrega}'.[/bold green]\n")
    else:
        chk_dict = cfg.checks.to_dict()
        if tool_clean in chk_dict and isinstance(chk_dict[tool_clean], dict):
            chk_dict[tool_clean][key] = val
            cfg.checks = ToolChecksConfig.from_dict(chk_dict)
            cfg.save()
            console.print(f"\n[bold green]✓ Chequeo global '{tool_clean}.{key} = {val}' guardado en dredd.yaml.[/bold green]\n")
        else:
            console.print(f"[bold red]Herramienta desconocida: '{tool}'. Válidas: ripley, kaneda, spunkmeyer, gaff, daedalus, sandbox.[/bold red]")
            raise typer.Exit(code=1)


@config_app.command("validate")
def cmd_config_validate(
    workspace: Path = typer.Option(Path("."), "--workspace", "-w", help="Directorio raíz del workspace."),
) -> None:
    """Valida la integridad de dredd.yaml, directorios del espacio de trabajo y existencia de guías Deckard."""
    from dredd.core.config import validate_workspace

    issues = validate_workspace(workspace)
    console.print(f"\n[bold cyan]─── Validación de Espacio de Trabajo Dredd: {workspace.resolve()} ───[/bold cyan]\n")

    has_errors = False
    for level, comp, msg in issues:
        if level == "OK":
            console.print(f"  [bold green]✓ [{comp}][/bold green] {msg}")
        elif level == "WARN":
            console.print(f"  [bold yellow]⚠ [{comp}][/bold yellow] {msg}")
        else:
            console.print(f"  [bold red]✗ [{comp}][/bold red] {msg}")
            has_errors = True

    console.print("")
    if has_errors:
        raise typer.Exit(code=1)


@config_app.command("preset")
def cmd_config_preset(
    preset_name: str = typer.Argument("strict", help="Nombre del preset a aplicar ('strict' o 'standard')."),
    workspace: Path = typer.Option(Path("."), "--workspace", "-w", help="Directorio raíz del workspace."),
) -> None:
    """Aplica un perfil preconfigurado de rigurosidad a dredd.yaml (ej. 'strict' para máxima rigurosidad)."""
    from dredd.core.config import load_dredd_config, ToolChecksConfig

    cfg = load_dredd_config(workspace)
    if not cfg:
        console.print(f"[bold red]No se encontró dredd.yaml en {workspace.resolve()}.[/bold red]")
        raise typer.Exit(code=1)

    if preset_name.lower() in ("strict", "estricto", "max", "maxima"):
        cfg.checks = ToolChecksConfig.get_strict_preset()
        cfg.workspace.name = f"{cfg.workspace.name} (Modo Máxima Rigurosidad)"
        cfg.save()
        console.print(f"\n[bold green]✓ Perfil de MÁXIMA RIGUROSIDAD ('strict') aplicado con éxito en dredd.yaml.[/bold green]")
        console.print("  • Daedalus: Flags estrictos (-Wall -Wextra -Werror -pedantic -std=c11 -Wconversion -Wshadow -fsanitize=address,undefined)")
        console.print("  • Ripley: Reglas P1 estrictas activadas al 100% (0 omisiones)")
        console.print("  • Kaneda: Prohibición total de llamadas riesgosas y evasión de sandbox")
        console.print("  • Spunkmeyer: Detección exhaustiva de todos los antipatrones C")
        console.print("  • Gaff: Cumplimiento estricto de estilo y guardas de header")
        console.print("  • Brett: 0 bytes de padding desperdiciado tolerado en structs")
        console.print("  • Bishop: Detección estricta de cualquier fuga de memoria (0 leaks)")
        console.print("  • Drake: Fuzzing de límites numéricos (INT_MAX/MIN) y strings vacíos")
        console.print("  • Sandbox: 32 MB RAM / 3.0s timeout / Fallo bloqueante en leaks o sanitizers\n")
    else:
        console.print(f"[bold red]Preset desconocido: '{preset_name}'. Disponibles: strict.[/bold red]")
        raise typer.Exit(code=1)


@app.command("doctor")
def cmd_doctor() -> None:
    """Verifica dependencias externas del sistema (GCC, Valgrind, Bubblewrap, Git, Ripley)."""
    from dredd.core.doctor import ejecutar_diagnostico_doctor
    ok = ejecutar_diagnostico_doctor(console=console)
    if not ok:
        raise typer.Exit(code=1)


@app.command("rerun")
def cmd_rerun(
    exercise: str = typer.Argument(..., help="Nombre de la actividad / ejercicio a re-evaluar."),
    student: Optional[str] = typer.Argument(None, help="Nombre de usuario del estudiante específico a re-evaluar (opcional)."),
    failed_only: bool = typer.Option(True, "--failed-only/--all-rerun", help="Re-evaluar únicamente entregas desaprobadas o con fallos de compilación."),
    tipo_entrega: Optional[str] = typer.Option(
        None,
        "--tipo-entrega",
        "--build-mode",
        "-m",
        help="Tipo de entrega / modo de construcción ('archivos_individuales', 'makefiles_individuales' o 'proyecto').",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Modo Dry Run: evalúa únicamente una muestra de hasta 3 estudiantes representativos.",
    ),
    workspace: Path = typer.Option(Path("."), "--workspace", "-w", help="Directorio raíz del workspace."),
) -> None:
    """Re-ejecuta la evaluación sobre entregas desaprobadas o con observaciones críticas."""
    from dredd.core.git_ops import resolve_submissions_dir
    exercise_slug, submissions_dir = resolve_submissions_dir(workspace, exercise)
    if not submissions_dir.exists():
        console.print(f"[bold red]No se encontró el directorio de entregas: {submissions_dir}[/bold red]")
        raise typer.Exit(code=1)

    console.print(f"[bold cyan]🔄 Re-evaluando entregas ({'solo fallidas' if failed_only else 'todas'}) para '{exercise_slug}'...[/bold cyan]")
    ejecutar_evaluacion(
        exercise=exercise_slug,
        student=student,
        all_students=(student is None),
        tipo_entrega=tipo_entrega,
        dry_run=dry_run,
        failed_only=failed_only,
        workspace_dir=workspace,
    )


@app.command("export-guarani")
@moodle_app.command("export-guarani")
def cmd_export_guarani(
    entregas: Path = typer.Argument(Path("entregas"), help="Directorio de entregas o base de datos de calificaciones."),
    output: Path = typer.Option(Path("acta_guarani.csv"), "--output", "-o", help="Ruta de destino del CSV de SIU Guaraní."),
) -> None:
    """Exporta las calificaciones finales en formato estándar de actas de SIU Guaraní."""
    from dredd.core.guarani import exportar_acta_guarani
    from dredd.core.reporter import find_student_report

    estudiantes = []
    if entregas.is_dir():
        for sub_dir in sorted(entregas.iterdir()):
            if sub_dir.is_dir() and not sub_dir.name.startswith((".", "_")) and sub_dir.name not in ("guia", "guide", "templates", "informe", "baseline", "_baseline"):
                rep = find_student_report(sub_dir)
                nota = 0.0
                if rep and rep.is_file():
                    # Parsear nota aproximada del informe
                    txt = rep.read_text(encoding="utf-8")
                    if "Nota:" in txt:
                        try:
                            nota = float(txt.split("Nota:")[1].split()[0])
                        except Exception:
                            nota = 7.0
                    else:
                        nota = 7.0
                estudiantes.append({"id": sub_dir.name, "nombre": sub_dir.name.replace("_", " ").title(), "nota": nota})

    if not estudiantes:
        estudiantes.append({"id": "12345", "nombre": "Alumno Demo", "nota": 8.0})

    out_file = exportar_acta_guarani(estudiantes, output)
    console.print(f"[bold green]✓ Acta para SIU Guaraní generada en:[/bold green] [cyan]{out_file}[/cyan]")


@app.command("dashboard")
@app.command("serve-dashboard")
def cmd_dashboard(
    port: int = typer.Option(8000, "--port", "-p", help="Puerto HTTP para el servidor de dashboard local."),
    host: str = typer.Option("127.0.0.1", "--host", "-H", help="Dirección IP o host local de escucha."),
    entregas: Path = typer.Option(Path("entregas"), "--entregas", "-e", help="Directorio con las entregas de los estudiantes para extraer notas."),
    data_file: Optional[Path] = typer.Option(None, "--data", "-d", help="Ruta a un archivo JSON con métricas precalculadas."),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Muestra información detallada de diagnóstico y registro de peticiones HTTP en consola."),
) -> None:
    """Inicia un servidor web local para visualizar el dashboard de notas y plagio."""
    from dredd.core.dashboard import recolectar_datos_dashboard, servir_dashboard

    data = recolectar_datos_dashboard(entregas_dir=entregas, data_json=data_file)
    try:
        servir_dashboard(
            data=data,
            port=port,
            host=host,
            verbose=verbose,
            console=console,
            entregas_path=entregas,
        )
    except OSError:
        raise typer.Exit(code=1)


@app.command("audit-git")
def cmd_audit_git(
    repo: Path = typer.Argument(Path("."), help="Ruta al repositorio de la entrega a auditar."),
) -> None:
    """Audita anomalías temporales y patrones de desarrollo en commits de Git."""
    from dredd.core.git_anomaly import auditar_historial_git
    auditar_historial_git(repo, console=console)


@app.command("export-feedback")
@app.command("notify-batch")
def cmd_export_feedback(
    entregas: Path = typer.Argument(Path("entregas"), help="Directorio con las entregas de los estudiantes."),
    output: Path = typer.Option(Path("feedbacks_lote"), "--output", "-o", help="Directorio de destino para los reportes."),
) -> None:
    """Empaqueta y exporta los informes individuales alumno_rN.md en un lote consolidado con ZIP."""
    from dredd.core.feedback_pack import empaquetar_devoluciones_batch
    empaquetar_devoluciones_batch(entregas, output, console=console)


@app.command("plagiarism-historical")
def cmd_plagiarism_historical(
    dir_actual: Path = typer.Argument(..., help="Directorio de entregas del cuatrimestre actual."),
    dir_historico: Path = typer.Argument(..., help="Directorio de entregas históricas de años previos."),
    umbral: float = typer.Option(0.70, "--threshold", "-t", help="Umbral de similitud mínima para alertar plagio."),
) -> None:
    """Detecta plagio cruzado inter-anual contra entregas históricas."""
    from dredd.core.plagiarism_history import comparar_plagio_historico
@app.command("diff-submission")
@app.command("diff-revision")
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







