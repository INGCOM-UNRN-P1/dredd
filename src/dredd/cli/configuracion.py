"""Configuración del curso: init y los comandos de `dredd config`."""

from pathlib import Path
from typing import Any, Dict, Optional
import typer
from rich.table import Table
from dredd.cli._base import _unwrap_cli_value, console  # noqa: F401


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
    t_map.add_column("Origen", justify="center")
    t_map.add_column("Patrón / Repo", style="yellow")
    t_map.add_column("Guía Deckard", style="green")
    t_map.add_column("Título")
    t_map.add_column("Overrides de Chequeo")

    for m in cfg.mapeos:
        overrides_str = ", ".join(f"{k}: {v}" for k, v in (m.checks or {}).items()) or "[dim]Hereda global[/dim]"
        src_label = "[cyan]GitHub[/cyan]" if getattr(m, "source", "moodle").lower() == "github" else "[magenta]Moodle[/magenta]"
        pat = getattr(m, "repo_pattern", None) if getattr(m, "source", "moodle").lower() == "github" else m.zip_pattern
        t_map.add_row(m.entrega, src_label, pat or m.zip_pattern, m.guia or "—", m.titulo or "—", overrides_str)

    console.print(t_map)
    console.print("")

    if entrega:
        eff = cfg.get_effective_checks(entrega)
        console.print(f"[bold cyan]Chequeos efectivos para '{entrega}':[/bold cyan]")
        console.print(f"  • Ripley: {eff.ripley_enabled} (Strict: {eff.ripley_strict}, Omitidas: {eff.ripley_disabled_rules or 'Ninguna'})")
        console.print(f"  • Seguridad Kaneda: {eff.kaneda_enabled}")
        console.print(f"  • Compilador: {eff.daedalus_compiler.upper()} ({eff.compiler_flags})")
        console.print(f"  • Sandbox: {eff.sandbox_memory_mb} MB RAM / {eff.sandbox_timeout_seconds}s\n")


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
    source: str = typer.Option("moodle", "--source", "-s", help="Origen de la entrega ('moodle' para ZIPs o 'github' para repositorios)."),
    github_org: Optional[str] = typer.Option(None, "--github-org", help="Organización de GitHub Classroom para esta entrega."),
    repo_pattern: Optional[str] = typer.Option(None, "--repo-pattern", help="Patrón o prefijo del nombre de repositorio en GitHub."),
    branch: Optional[str] = typer.Option("main", "--branch", help="Rama por defecto para clonar/evaluar en GitHub."),
    workspace: Path = typer.Option(Path("."), "--workspace", "-w", help="Directorio raíz del workspace."),
) -> None:
    """Agrega o actualiza una entrega en dredd.yaml con su patrón ZIP, origen Moodle/GitHub, guía Deckard, modo y chequeos específicos."""
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
        source=source,
        github_org=github_org,
        repo_pattern=repo_pattern,
        branch=branch,
    )
    cfg.add_or_update_mapping(rule)
    cfg.save()

    console.print(f"\n[bold green]✓ Entrega '{entrega}' guardada exitosamente en dredd.yaml:[/bold green]")
    console.print(f"  • [bold]Origen:[/bold] [cyan]{source.upper()}[/cyan]")
    if source.lower() == "github" or repo_pattern:
        console.print(f"  • [bold]GitHub Org:[/bold] [cyan]{github_org or cfg.workspace.default_org}[/cyan]")
        console.print(f"  • [bold]Patrón Repo:[/bold] [yellow]{repo_pattern or entrega + '-*'}[/yellow]")
        console.print(f"  • [bold]Rama:[/bold] [magenta]{branch or 'main'}[/magenta]")
    else:
        console.print(f"  • [bold]Patrón ZIP:[/bold] [yellow]{zip_pattern}[/yellow]")
    console.print(f"  • [bold]Guía Deckard:[/bold] [cyan]{guia or 'No asignada'}[/cyan]")
    console.print(f"  • [bold]Modo de entrega:[/bold] [magenta]{mode or 'Auto / Heredado'}[/magenta]")
    console.print(f"  • [bold]Título:[/bold] {titulo or '—'}")
    if checks_dict:
        console.print(f"  • [bold]Overrides de chequeo:[/bold] {checks_dict}\n")


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
