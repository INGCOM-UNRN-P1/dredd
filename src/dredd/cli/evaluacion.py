"""Evaluación de entregas: eval, evaluate run/clean, rerun y sus variantes."""

from pathlib import Path
from typing import Any, Dict, List, Optional
import typer
from rich.table import Table
from rich.panel import Panel
from dredd.core.git_ops import ensure_submission_repo, get_repo_metadata, resolve_submissions_dir
from dredd.core.guide_integration import load_activity_guide
from dredd.core.reporter import generate_student_report
from dredd.core.ripley_client import run_ripley_analysis
from dredd.cli._base import _unwrap_cli_value, console  # noqa: F401


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
    json_output: bool = False,
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
    workspace_dir = _unwrap_cli_value(workspace_dir, None)
    if workspace_dir is not None and not isinstance(workspace_dir, Path):
        workspace_dir = Path(workspace_dir)
    json_output = bool(_unwrap_cli_value(json_output, False))
    ws_dir = (workspace_dir or Path.cwd()).resolve()

    exercise_slug, submissions_dir = resolve_submissions_dir(ws_dir, exercise)
    guide = load_activity_guide(submissions_dir, exercise_slug, ws_dir)

    # Determinar modo de construcción efectivo con precedencia: CLI override > dredd.yaml > Guía Deckard > Auto > Default
    from dredd.core.config import DreddConfig, load_dredd_config
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
        if not json_output:
            console.print(f"[bold green]✓ Guía Deckard conectada ('{guide.nombre}'): {len(guide.exercises)} ejercicio(s) ({', '.join(guide.get_exercise_ids())}) | Modo: {effective_tipo}[/bold green]")
    else:
        if not json_output:
            console.print(f"[bold blue]Modo de construcción activo: {effective_tipo}[/bold blue]")

    table = Table(title=f"Evaluación Dredd — {exercise_slug}")
    table.add_column("Estudiante", style="cyan", justify="left")
    table.add_column("Compilación", justify="center")
    table.add_column("Tests", justify="center")
    table.add_column("Reglas P1 / AST", justify="center")
    table.add_column("Informe", style="green")

    json_results: List[Dict[str, Any]] = []

    for s_name in target_students:
        if not json_output:
            console.print(f"[bold]Procesando estudiante:[/bold] [cyan]{s_name}[/cyan]...")

        try:
            repo_path = ensure_submission_repo(org, exercise_slug, s_name, ws_dir, submissions_dir=submissions_dir)
        except Exception as e:
            if not json_output:
                console.print(f"  [red]Error al obtener repositorio:[/red] {e}")
                table.add_row(s_name, "[red]ERROR[/red]", "—", "—", "No generado")
            else:
                json_results.append({
                    "student": s_name,
                    "success": False,
                    "error": str(e),
                })
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

            try:
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

                json_results.append({
                    "student": s_name,
                    "revision": rev_str,
                    "compilation_ok": comp_ok,
                    "tests_passed": tests_info.get("passed", 0),
                    "tests_total": tests_info.get("total", 0),
                    "ast_observations": ast_count,
                    "report_file": str(report_file),
                })
            except Exception as e:
                import traceback
                error_trace = traceback.format_exc()
                if not json_output:
                    console.print(f"  [bold red]Error fatal durante la evaluación de {s_name} ({rev_str}):[/bold red] {e}")
                    console.print(f"[dim]{error_trace.strip()}[/dim]")
                    table.add_row(f"{s_name} [{rev_str}]", "[red]ERROR[/red]", "—", "—", f"Fallo: {e}")
                else:
                    json_results.append({
                        "student": s_name,
                        "revision": rev_str,
                        "compilation_ok": False,
                        "tests_passed": 0,
                        "tests_total": 0,
                        "ast_observations": 0,
                        "report_file": str(report_file),
                        "error": str(e),
                        "traceback": error_trace,
                    })

    if json_output:
        import json
        print(json.dumps({
            "exercise": exercise_slug,
            "total_students": len(json_results),
            "results": json_results,
        }, indent=2, ensure_ascii=False))
    else:
        console.print("\n")
        console.print(table)
        console.print("\n[dim]Para enviar los comentarios a los PRs correspondientes, ejecute: dredd github comment <ejercicio> <estudiante>[/dim]\n")


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
    clean: bool = typer.Option(
        False,
        "--clean",
        "-c",
        help="Limpia directorios de evaluación (rNi) e informes previos antes de volver a evaluar.",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Fuerza la re-evaluación completa eliminando resultados previos de las carpetas de estudiantes.",
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Emite el resultado estructurado de la evaluación en formato JSON (máquina a máquina).",
    ),
    workspace: Path = typer.Option(
        Path("."),
        "--workspace",
        "-w",
        help="Directorio raíz del workspace.",
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

    if clean or force:
        ejecutar_limpieza_evaluaciones(
            exercise=exercise,
            student=student,
            all_students=all_students,
            dry_run=False,
        )

    ejecutar_evaluacion(
        exercise=exercise,
        student=student,
        org=org,
        all_students=all_students,
        template_dir=template_dir,
        tipo_entrega=tipo_entrega,
        dry_run=dry_run,
        baseline=baseline,
        json_output=json_output,
        workspace_dir=workspace,
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
    clean: bool = typer.Option(
        False,
        "--clean",
        "-c",
        help="Limpia directorios de evaluación (rNi) e informes previos antes de volver a evaluar.",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Fuerza la re-evaluación completa eliminando resultados previos de las carpetas de estudiantes.",
    ),
) -> None:
    """Clona/actualiza el repositorio o evalúa entregas locales, ejecuta el análisis con Ripley y genera el informe Markdown."""
    if clean or force:
        ejecutar_limpieza_evaluaciones(
            exercise=exercise,
            student=student,
            all_students=all_students,
            dry_run=False,
        )

    ejecutar_evaluacion(
        exercise=exercise,
        student=student,
        org=org,
        all_students=all_students,
        template_dir=template_dir,
        tipo_entrega=tipo_entrega,
        dry_run=dry_run,
    )


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


def cmd_late_penalty(
    fecha_entrega: str = typer.Argument(..., help="Fecha y hora de entrega (ISO o 'YYYY-MM-DD HH:MM')."),
    fecha_limite: str = typer.Argument(..., help="Fecha y hora límite de entrega (ISO o 'YYYY-MM-DD HH:MM')."),
    nota: float = typer.Option(10.0, "--nota", "-n", help="Calificación base antes de la penalización."),
    gracia: int = typer.Option(15, "--gracia", "-g", help="Minutos de gracia sin penalización."),
    tasa: float = typer.Option(0.25, "--tasa", "-t", help="Puntos de descuento por cada hora de retraso."),
    max_descuento: float = typer.Option(4.0, "--max-descuento", "-m", help="Tope máximo de puntos de descuento."),
    json_output: bool = typer.Option(False, "--json", help="Emitir resultado en formato JSON."),
) -> None:
    """Calcula la penalización gradual por entrega fuera de término."""
    from datetime import datetime
    import json
    from dredd.core.late_penalty import calcular_penalizacion_entrega

    def parse_dt(s: str) -> datetime:
        try:
            return datetime.fromisoformat(s)
        except ValueError:
            pass
        try:
            return datetime.strptime(s, "%Y-%m-%d %H:%M")
        except ValueError:
            raise typer.BadParameter(
                f"«{s}» no es una fecha válida: usá ISO 8601 o el formato AAAA-MM-DD HH:MM "
                "(por ejemplo 2026-09-25 23:59)."
            ) from None

    dt_entrega = parse_dt(fecha_entrega)
    dt_limite = parse_dt(fecha_limite)

    info = calcular_penalizacion_entrega(
        fecha_entrega=dt_entrega,
        fecha_limite=dt_limite,
        nota_original=nota,
        gracia_minutos=gracia,
        puntos_por_hora=tasa,
        max_descuento=max_descuento,
    )

    if json_output:
        print(json.dumps(info.to_dict(), indent=2, ensure_ascii=False))
        return

    color = "green" if info.a_tiempo else "yellow" if info.puntos_descuento < max_descuento else "red"
    console.print(Panel(
        f"• **Estado:** [{color}]{'A tiempo' if info.a_tiempo else 'Fuera de término'}[/{color}]\n"
        f"• **Minutos de retraso:** {info.minutos_retraso:.1f} min ({info.horas_retraso:.2f} h)\n"
        f"• **Descuento aplicado:** -{info.puntos_descuento:.2f} pts\n"
        f"• **Nota ajustada:** [bold {color}]{info.nota_final:.2f} / {info.nota_original:.2f}[/bold {color}]\n\n"
        f"_{info.detalle}_",
        title="[bold cyan]Dredd Late Penalty Calculator[/bold cyan]",
        border_style=color,
    ))


def cmd_typology(
    directorio: Path = typer.Argument(..., exists=True, help="Directorio de la entrega del alumno o carpeta de entregas."),
    json_output: bool = typer.Option(False, "--json", help="Salida en formato JSON."),
) -> None:
    """Clasifica automáticamente la tipología arquitectónica de una entrega (monolítica, modular, librería, incompleta)."""
    import json
    from dredd.core.submission_typology import clasificar_tipologia_entrega

    reporte = clasificar_tipologia_entrega(directorio)
    if json_output:
        print(json.dumps(reporte.to_dict(), indent=2, ensure_ascii=False))
        return

    tipo_colores = {
        "modular": "green",
        "monolitica": "yellow",
        "libreria_tda": "cyan",
        "incompleta": "red",
    }
    color = tipo_colores.get(reporte.tipologia.value, "white")

    console.print(Panel(
        f"• **Tipología:** [bold {color}]{reporte.tipologia.value.upper()}[/bold {color}]\n"
        f"• **Archivos C:** {reporte.cant_c} ({', '.join(reporte.archivos_c) if reporte.archivos_c else 'ninguno'})\n"
        f"• **Cabeceras H:** {reporte.cant_h} ({', '.join(reporte.archivos_h) if reporte.archivos_h else 'ninguna'})\n"
        f"• **Líneas de código (LOC):** {reporte.total_loc}\n"
        f"• **Posee main():** {'Sí' if reporte.tiene_main else 'No'}\n"
        f"• **Posee Makefile:** {'Sí' if reporte.tiene_makefile else 'No'}\n\n"
        f"_{reporte.diagnostico}_",
        title=f"[bold cyan]Tipología de Entrega: {reporte.estudiante_o_dir}[/bold cyan]",
        border_style=color,
    ))


def cmd_eval_stability(
    binario: Path = typer.Argument(..., exists=True, help="Ruta al binario ejecutable C."),
    repeticiones: int = typer.Option(5, "--repeticiones", "-n", help="Número de ejecuciones consecutivas."),
    input_data: str = typer.Option("", "--input", "-i", help="Datos de entrada stdin para el proceso."),
    timeout: float = typer.Option(3.0, "--timeout", "-t", help="Timeout por corrida en segundos."),
    json_output: bool = typer.Option(False, "--json", help="Salida en formato JSON."),
) -> None:
    """Evalúa la estabilidad temporal y determinismo de una solución mediante corridas reiteradas."""
    import json
    from dredd.core.stability_eval import evaluar_estabilidad_binario

    res = evaluar_estabilidad_binario(binario, input_data=input_data, repeticiones=repeticiones, timeout_seg=timeout)
    if json_output:
        print(json.dumps(res.to_dict(), indent=2, ensure_ascii=False))
        return

    color = "green" if res.estable else "red"
    console.print(Panel(
        f"• **Estable:** [{color}]{'SÍ (100% Determinista)' if res.estable else 'NO (Comportamiento Flaky)'}[/{color}]\n"
        f"• **Corridas totales:** {res.total_corridas}\n"
        f"• **Salidas distintas:** {res.salidas_distintas}\n"
        f"• **Códigos de retorno observados:** {res.codigos_retorno}\n"
        f"• **Latencia promedio:** {sum(res.duraciones_ms)/len(res.duraciones_ms):.2f} ms\n\n"
        f"_{res.detalle}_",
        title=f"[bold cyan]Evaluación de Estabilidad: {res.ejecutable}[/bold cyan]",
        border_style=color,
    ))


def cmd_cohort_bench(
    entregas: Path = typer.Argument(..., exists=True, help="Directorio contenedor de las entregas de la cohorte."),
    binario: str = typer.Option("main", "--bin", "-b", help="Nombre del archivo binario ejecutable a comparar."),
    input_data: str = typer.Option("", "--input", "-i", help="Datos de entrada para el benchmark."),
    timeout: float = typer.Option(5.0, "--timeout", "-t", help="Timeout máximo por entrega en segundos."),
    json_output: bool = typer.Option(False, "--json", help="Salida en formato JSON."),
) -> None:
    """Ejecuta benchmarking algorítmico comparativo de CPU y memoria en toda la cohorte."""
    import json
    from dredd.core.cohort_bench import comparar_desempeno_cohorte

    rep = comparar_desempeno_cohorte(entregas, nombre_binario=binario, input_data=input_data, timeout_seg=timeout)
    if json_output:
        print(json.dumps(rep.to_dict(), indent=2, ensure_ascii=False))
        return

    tabla = Table(title=f"Benchmarking de Cohorte ({rep.total_evaluados} entregas)", border_style="cyan")
    tabla.add_column("Puesto", justify="right", style="bold")
    tabla.add_column("Estudiante", style="bold white")
    tabla.add_column("Tiempo (ms)", justify="right", style="green")
    tabla.add_column("Memoria RSS (KB)", justify="right", style="yellow")
    tabla.add_column("Estado", justify="center")

    for i, m in enumerate(rep.ranking, 1):
        est_str = "[green]OK[/green]" if m.ok else f"[red]FAIL ({m.exit_code})[/red]"
        tabla.add_row(str(i), m.estudiante, f"{m.tiempo_ms:.2f} ms", f"{m.memoria_rss_kb} KB", est_str)

    console.print(tabla)
    console.print(
        f"[dim]Tiempos: Promedio = {rep.tiempo_promedio_ms:.2f} ms | Mediana = {rep.tiempo_mediana_ms:.2f} ms | "
        f"Memoria promedio = {rep.memoria_promedio_kb:.1f} KB[/dim]"
    )


def cmd_smith_adversary(
    target: Path = typer.Argument(..., exists=True, help="Ruta a binario ejecutable o directorio de tests para inyección."),
    inject: bool = typer.Option(False, "--inject", help="Inyectar casos adversarios .in en la carpeta destino."),
    timeout: float = typer.Option(2.0, "--timeout", "-t", help="Timeout por caso adversario en segundos."),
    json_output: bool = typer.Option(False, "--json", help="Salida en formato JSON."),
) -> None:
    """Genera e inyecta casos de prueba adversarios y de estrés (integración smith)."""
    import json
    from dredd.core.smith_adversary import inyectar_casos_adversarios, evaluar_con_casos_adversarios

    if inject or target.is_dir():
        rutas = inyectar_casos_adversarios(target if target.name == "tests" else target / "tests")
        console.print(f"[bold green]✓ Inyectados {len(rutas)} casos adversarios en:[/bold green] [cyan]{target}[/cyan]")
        return

    if not target.is_file():
        console.print(f"[bold red]El archivo binario '{target}' no existe.[/bold red]")
        raise typer.Exit(code=1)

    rep = evaluar_con_casos_adversarios(target, timeout_seg=timeout)
    if json_output:
        print(json.dumps(rep.to_dict(), indent=2, ensure_ascii=False))
        return

    color = "green" if rep.crashes == 0 else "red"
    console.print(Panel(
        f"• **Estudiante:** {rep.estudiante}\n"
        f"• **Casos superados:** [green]{rep.casos_superados} / {rep.total_casos}[/green]\n"
        f"• **Crashes (SIGSEGV/ABRT/Timeout):** [{color}]{rep.crashes}[/{color}]",
        title="[bold cyan]Resultados de Pruebas Adversarias (Smith)[/bold cyan]",
        border_style=color,
    ))

    tabla = Table(title="Detalle de Casos Adversarios", border_style="dim")
    tabla.add_column("Caso", style="bold")
    tabla.add_column("Estado", justify="center")
    tabla.add_column("Código", justify="right")
    tabla.add_column("Detalle")

    for d in rep.detalles:
        est_style = "[green]OK[/green]" if d["estado"] == "OK" else f"[bold red]{d['estado']}[/bold red]"
        tabla.add_row(d["caso"], est_style, d["codigo"], d["mensaje"])

    console.print(tabla)


def cmd_eval_shielded(
    cmd: str = typer.Argument(..., help="Comando binario a ejecutar en sandbox blindado."),
    input_data: str = typer.Option("", "--input", "-i", help="Entrada stdin."),
    timeout: float = typer.Option(3.0, "--timeout", "-t", help="Timeout máximo en segundos."),
    memoria_mb: int = typer.Option(48, "--memory", "-m", help="Límite estricto de memoria en MB."),
) -> None:
    """Ejecuta un proceso bajo el modo 'Sandbox Blindado' con corte total de red y namespaces aislados."""
    import shlex
    from dredd.core.sandbox import execute_shielded_sandbox

    args = shlex.split(cmd)
    retcode, out, err, timed_out = execute_shielded_sandbox(
        args,
        input_data=input_data,
        timeout=timeout,
        max_memory_mb=memoria_mb,
    )
    console.print(f"[bold cyan]Código de salida:[/bold cyan] {retcode}")
    if timed_out:
        console.print("[bold red]Ejecución interrumpida por límite de recursos o timeout.[/bold red]")
    if out:
        console.print(f"[bold green]STDOUT:[/bold green]\n{out}")
    if err:
        console.print(f"[bold yellow]STDERR:[/bold yellow]\n{err}")
    # El código del proceso aislado; si no se pudo ejecutar (-1) o se cortó, 1. Antes siempre 0 (N-ECO-18).
    raise typer.Exit(code=retcode if 0 <= retcode <= 255 and not timed_out else 1)
