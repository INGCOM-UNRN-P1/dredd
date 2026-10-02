"""Análisis transversales: plagio, mapa de entregas, fuzzing, guías orales y auditorías."""

from pathlib import Path
import json
from typing import List, Optional
import typer
from rich.console import Console
from rich.table import Table
from dredd.core.git_ops import resolve_submissions_dir
from dredd.core.guide_integration import load_activity_guide
from dredd.core.plagiarism import PlagiarismDetector
from dredd.cli._base import _unwrap_cli_value, console  # noqa: F401

_err = Console(stderr=True)


def _aviso_traslado(comando: str, reemplazo: str) -> None:
    """Los comandos duplicados pasan a su herramienta dueña (revisión 04 §5, N-ECO-12)."""
    _err.print(f"[yellow]Aviso:[/yellow] `dredd {comando}` pasa a `{reemplazo}` y se va a retirar.")


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
    if not submissions_dir.is_dir():
        # El resolvedor devuelve la carpeta por omisión para descargas nuevas; acá tiene que existir:
        # antes respondía «No se encontraron archivos .c para mapear» con código 0 (N-ECO-18).
        Console(stderr=True).print(f"[bold red]Error:[/bold red] no hay entregas de «{activity}»: no existe {submissions_dir}.")
        raise typer.Exit(code=2)
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
    _aviso_traslado("fuzz-gen", "drake gen-casos")
    try:  # con el extra `ecosistema`, el generador de drake (el dueño del fuzzing)
        from drake.core.generar_casos import generar_testcases
    except ImportError:
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


def cmd_multiplex(
    spec: Path = typer.Option(..., "--spec", "-s", exists=True, help="Ruta al archivo matriz.yaml."),
    students: Optional[Path] = typer.Option(None, "--students", exists=True, help="CSV con lista de alumnos."),
    salida: Path = typer.Option(Path("dist/multiplex"), "--salida", "-o", help="Directorio destino de la multiplexación."),
    pack: bool = typer.Option(True, "--pack/--no-pack", help="Generar paquetes .ripkg para cada variante."),
    starters: bool = typer.Option(True, "--starters/--no-starters", help="Generar starter repos por alumno."),
) -> None:
    """Alias docente de conveniencia que delega la generación de variantes y asignación en Deckard."""
    import subprocess
    from dredd.core.ecosystem import resolve_sibling_cli, resolve_sibling_tool

    # 1. Intentar ejecución vía CLI de deckard
    deckard_bin = resolve_sibling_cli("deckard")
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
    multiplexar_tp = resolve_sibling_tool("deckard", "deckard.core.multiplex", "multiplexar_tp")
    if multiplexar_tp is not None:
        try:
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
            return
        except Exception as e:
            console.print(f"[bold red]Error en multiplex:[/bold red] {e}")
            raise typer.Exit(code=1)

    console.print("[bold red]Deckard no está disponible en PATH ni en el entorno hermano.[/bold red]")
    console.print("  ↳ Instalar o enlazar Deckard: [cyan]pip install -e ../deckard[/cyan]")
    raise typer.Exit(code=1)


def cmd_doctor(
    json_output: bool = typer.Option(False, "--json", help="Emitir el diagnóstico como JSON (schema_version 1.0.0)."),
) -> None:
    """Verifica dependencias externas del sistema (GCC, Valgrind, Bubblewrap, Git, Ripley)."""
    from dredd.core.doctor import diagnosticar, ejecutar_diagnostico_doctor, informe_json
    if json_output:
        informe = informe_json(diagnosticar())
        print(json.dumps(informe, ensure_ascii=False, indent=2))
        if not informe["ok"]:
            raise typer.Exit(code=1)
        return
    ok = ejecutar_diagnostico_doctor(console=console)
    if not ok:
        raise typer.Exit(code=1)


def cmd_plagiarism_historical(
    dir_actual: Path = typer.Argument(..., exists=True, help="Directorio de entregas del cuatrimestre actual."),
    dir_historico: Path = typer.Argument(..., exists=True, help="Directorio de entregas históricas de años previos."),
    umbral: float = typer.Option(0.70, "--threshold", "-t", help="Umbral de similitud mínima para alertar plagio."),
) -> None:
    """Detecta plagio cruzado inter-anual contra entregas históricas."""


def cmd_audit_makefile(
    objetivo: Path = typer.Argument(..., exists=True, help="Ruta al archivo Makefile o al directorio de la entrega."),
    json_output: bool = typer.Option(False, "--json", help="Salida en formato JSON."),
) -> None:
    """Audita Makefiles en busca de dependencias prohibidas, flags suprimidas y trampas."""
    import json

    _aviso_traslado("audit-makefile", "wierzbowski makefile")
    from dredd.core.makefile_audit import auditar_makefile

    mk_path = objetivo if objetivo.is_file() else (objetivo / "Makefile" if (objetivo / "Makefile").is_file() else objetivo / "makefile")
    if not mk_path.is_file():
        console.print(f"[bold red]No se encontró archivo Makefile en:[/bold red] {objetivo}")
        raise typer.Exit(code=1)

    findings = auditar_makefile(mk_path)
    if json_output:
        print(json.dumps([f.to_dict() for f in findings], indent=2, ensure_ascii=False))
        return

    if not findings:
        console.print(f"[bold green]✓ Makefile conforme:[/bold green] Sin dependencias prohibidas ni trampas detectadas en {mk_path}.")
        return

    tabla = Table(title=f"Auditoría de Makefile: {mk_path.name}", border_style="red")
    tabla.add_column("Línea", justify="right", style="cyan")
    tabla.add_column("Severidad", justify="center")
    tabla.add_column("Regla", style="bold")
    tabla.add_column("Mensaje")
    tabla.add_column("Código", style="dim")

    for f in findings:
        sev_style = "[bold red]TRAMPA[/bold red]" if f.severidad == "TRAMPA" else "[red]ERROR[/red]" if f.severidad == "ERROR" else "[yellow]ADV[/yellow]"
        tabla.add_row(str(f.linea), sev_style, f.regla, f.mensaje, f.codigo[:40])

    console.print(tabla)
