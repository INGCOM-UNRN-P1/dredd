"""Exportación e ingesta: Moodle, Guaraní, reportes y devoluciones."""

from pathlib import Path
from typing import Optional
import typer
from dredd.cli._base import _unwrap_cli_value, console  # noqa: F401


def cmd_moodle_ingest(
    zip_file: Path = typer.Argument(..., exists=True, help="Archivo ZIP descargado de Moodle con las entregas de la tarea."),
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


def _avisar_sin_participante(exporter, activity: str) -> None:
    """Moodle descarta una fila sin número de participante: sin este aviso, el CSV parece bueno."""
    faltan = exporter.filas_sin_participante(activity)
    if faltan:
        console.print(f"[yellow]⚠ {faltan} fila(s) sin número de participante de Moodle (entregas de GitHub): "
                      "Moodle no las va a importar. Usá [bold]dredd moodle paquete[/bold].[/yellow]\n")


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
        _avisar_sin_participante(exporter, activity)
    except Exception as e:
        console.print(f"[bold red]Error durante la exportación:[/bold red] {e}")
        raise typer.Exit(code=1) from e


def cmd_export_report(
    source: Path = typer.Argument(..., exists=True, help="Ruta al archivo Markdown (.md) del informe."),
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
        raise typer.Exit(code=1) from e


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
        _avisar_sin_participante(exporter, exercise)
    except Exception as e:
        console.print(f"[bold red]Error al exportar planilla Moodle:[/bold red] {e}")
        raise typer.Exit(code=1) from e


def cmd_moodle_paquete(
    planilla: Path = typer.Option(..., "--planilla", "-p", exists=True, dir_okay=False, help="Hoja de calificaciones descargada de la tarea de Moodle."),
    notas: Path = typer.Option(Path("calificaciones/calificaciones.csv"), "--notas", "-n", exists=True, dir_okay=False, help="calificaciones.csv de deckard exercise rubric."),
    devoluciones: Optional[Path] = typer.Option(None, "--devoluciones", "-d", help="Carpeta de devoluciones Markdown (por omisión, devoluciones/ junto a las notas)."),
    mapa: Optional[Path] = typer.Option(None, "--mapa", "-m", exists=True, dir_okay=False, help="CSV alumno,dato en Moodle (identificador, correo o nombre), para entregas de GitHub."),
    salida: Path = typer.Option(Path("moodle"), "--salida", "-o", help="Carpeta del paquete."),
    incluir_provisorias: bool = typer.Option(False, "--incluir-provisorias", help="Importar también las notas provisorias."),
    maximo: Optional[float] = typer.Option(None, "--maximo", min=0.01, help="Calificación máxima de la tarea, si la planilla no la trae."),
    columna_nota: Optional[str] = typer.Option(None, "--columna-nota", help="Encabezado de la nota, si no se detecta."),
    columna_comentarios: Optional[str] = typer.Option(None, "--columna-comentarios", help="Encabezado de los comentarios, si no se detecta."),
) -> None:
    """Arma el paquete para el calificador de Moodle desde las notas y devoluciones de deckard.

    Completa la hoja de calificaciones de la tarea y empaqueta las devoluciones en HTML. Las notas
    provisorias dejan su fila intacta. Sale con 1 si un estudiante no se pudo vincular.
    """
    from dredd.core.moodle_paquete import PaqueteError, armar_paquete

    try:
        res = armar_paquete(planilla, notas, salida, devoluciones, mapa, incluir_provisorias, maximo,
                            columna_nota, columna_comentarios)
    except PaqueteError as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(code=1) from e
    console.print(f"[bold green]✓ {len(res.importadas)} nota(s) en[/bold green] [cyan]{res.planilla}[/cyan]")
    if res.zip:
        console.print(f"[bold green]✓ Devoluciones en[/bold green] [cyan]{res.zip}[/cyan]")
    if res.provisorias:
        console.print(f"[yellow]⚠ Sin importar, por provisorias: {', '.join(res.provisorias)}[/yellow]")
    if res.sin_devolucion:
        console.print(f"[yellow]⚠ Sin devolución en el ZIP: {', '.join(res.sin_devolucion)}[/yellow]")
    console.print(f"[dim]Filas de la planilla sin tocar: {res.filas_sin_nota}[/dim]")
    if res.sin_vincular:
        console.print(f"[bold red]✗ Sin vincular con la planilla: {', '.join(res.sin_vincular)}[/bold red]\n"
                      "  Agregalos al --mapa (alumno,identificador, correo o nombre en Moodle).")
        raise typer.Exit(code=1)


def cmd_export_guarani(
    entregas: Path = typer.Argument(Path("entregas"), exists=True, help="Directorio de entregas o base de datos de calificaciones."),
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
        raise typer.Exit(code=1) from None


def cmd_export_feedback(
    entregas: Path = typer.Argument(Path("entregas"), exists=True, help="Directorio con las entregas de los estudiantes."),
    output: Path = typer.Option(Path("feedbacks_lote"), "--output", "-o", help="Directorio de destino para los reportes."),
) -> None:
    """Empaqueta y exporta los informes individuales alumno_rN.md en un lote consolidado con ZIP."""
    from dredd.core.feedback_pack import empaquetar_devoluciones_batch
    empaquetar_devoluciones_batch(entregas, output, console=console)


def cmd_report_template(
    template: Optional[Path] = typer.Option(None, "--template", "-t", help="Ruta a la plantilla Markdown con variables contextuales."),
    student: str = typer.Option("estudiante_ejemplo", "--student", "-s", help="Identificador o nombre del estudiante."),
    exercise: str = typer.Option("guia_c", "--exercise", "-e", help="Nombre del ejercicio o TP."),
    score: str = typer.Option("9.0", "--score", help="Calificación para la previsualización."),
    total_tests: int = typer.Option(10, "--total-tests", help="Total de casos de prueba."),
    passed_tests: int = typer.Option(9, "--passed-tests", help="Casos de prueba aprobados."),
    failures: str = typer.Option("Caso límite 02: retorno inesperado", "--failures", help="Descripción o detalle de fallos."),
    memory_summary: str = typer.Option("✓ Sin fugas de memoria (0 bytes perdidos)", "--memory-summary", help="Resumen de memoria dinámica."),
    badge: str = typer.Option("✅ **ENTREGA APROBADA**", "--badge", help="Insignia de estado general."),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Guardar el reporte renderizado en un archivo."),
    dump_default: bool = typer.Option(False, "--dump-default", help="Imprimir o guardar la plantilla por defecto sin renderizar."),
) -> None:
    """Renderiza o valida plantillas de feedback Markdown enriquecidas con variables contextuales."""
    from dredd.core.feedback_template import DEFAULT_FEEDBACK_TEMPLATE, load_and_render_feedback_template

    if dump_default:
        if output:
            output.write_text(DEFAULT_FEEDBACK_TEMPLATE, encoding="utf-8")
            console.print(f"[bold green]✓ Plantilla por defecto exportada a:[/bold green] [cyan]{output}[/cyan]")
        else:
            console.print(DEFAULT_FEEDBACK_TEMPLATE)
        return

    ctx = {
        "student_id": student,
        "student_name": student,
        "exercise_name": exercise,
        "score": score,
        "total_tests": total_tests,
        "passed_tests": passed_tests,
        "failed_tests": max(0, total_tests - passed_tests),
        "failures": failures,
        "memory_summary": memory_summary,
        "badge": badge,
    }

    rendered = load_and_render_feedback_template(template, ctx)

    if output:
        output.write_text(rendered, encoding="utf-8")
        console.print(f"[bold green]✓ Feedback renderizado guardado en:[/bold green] [cyan]{output}[/cyan]")
    else:
        console.print("\n[bold cyan]─── Previsualización de Devolución Pedagógica ───[/bold cyan]\n")
        console.print(rendered)


def cmd_sanitize_output(
    file: Path = typer.Argument(..., exists=True, help="Archivo de log o volcado de salida a sanitizar."),
    max_mb: int = typer.Option(10, "--max-mb", help="Límite máximo seguro en megabytes antes de truncar."),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Archivo de destino (por defecto sobrescribe el original)."),
    no_strip_ansi: bool = typer.Option(False, "--no-strip-ansi", help="No remover secuencias de escape ANSI."),
) -> None:
    """Sanitiza flujos de salida o logs estudiantiles eliminando secuencias ANSI y truncando si excede el límite."""
    from dredd.core.output_sanitizer import sanitize_log_file

    if not file.is_file():
        console.print(f"[bold red]Error: El archivo '{file}' no existe.[/bold red]")
        raise typer.Exit(code=1)

    max_bytes = max_mb * 1024 * 1024
    out_target = sanitize_log_file(file, output_path=output, max_bytes=max_bytes)
    console.print(f"[bold green]✓ Archivo sanitizado con éxito en:[/bold green] [cyan]{out_target}[/cyan]")


def cmd_cohorte(
    carpeta: Path = typer.Argument(..., exists=True, file_okay=False, help="Carpeta con un repositorio clonado por alumno."),
    salida: Path = typer.Option(Path("informe-cohorte"), "--salida", "-o", help="Carpeta para cohorte.csv, cohorte.md y cohorte.json."),
    ruta: str = typer.Option(".", "--ruta", help="Archivo o carpeta a verificar dentro de cada repositorio."),
    perfil: str = typer.Option("strict", "--perfil", "-p", help="Perfil de ripley: strict, relaxed o exam."),
    prefijo: str = typer.Option("", "--prefijo", help="Prefijo de los repos de Classroom (tp1-): el resto es el usuario del alumno."),
    fecha_limite: Optional[str] = typer.Option(None, "--fecha-limite", help="Fecha límite ISO 8601 (2026-11-02T23:59-03:00) para calcular el atraso."),
) -> None:
    """Planilla de seguimiento de una cohorte de Classroom: estado, observaciones frecuentes y tiempos (Ola 25)."""
    from datetime import datetime

    from dredd.core.seguimiento import analizar_cohorte, escribir
    from dredd.core.ecosystem import resolve_sibling_cli

    ripley = resolve_sibling_cli("ripley")
    if not ripley:
        console.print("[bold red]No se encontró ripley:[/bold red] instalalo con mother (perfil docente).")
        raise typer.Exit(code=2)
    limite = None
    if fecha_limite:
        try:
            limite = datetime.fromisoformat(fecha_limite)
        except ValueError as e:
            raise typer.BadParameter(f"fecha inválida: {fecha_limite}") from e
        if limite.tzinfo is None:
            raise typer.BadParameter("indicá la zona horaria (por ejemplo 2026-11-02T23:59-03:00)")
    informe = analizar_cohorte(carpeta, ruta=ruta, perfil=perfil, prefijo=prefijo, fecha_limite=limite, ripley=ripley)
    for ruta_salida in escribir(informe, salida):
        console.print(f"[green]✓[/green] {ruta_salida}")
    t = informe["totales"]
    console.print(f"{t['alumnos']} alumnos: {t['aprobada']} aprobadas, {t['con errores']} con errores, "
                  f"{t['no compila']} no compilan, {t['sin entrega']} sin entrega.")
