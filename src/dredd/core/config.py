"""Gestión de configuración declarativa del espacio de trabajo de Dredd (dredd.yaml).

Soporta configuración centralizada de espacio de trabajo, mapeos ZIP-a-guía
y políticas de verificación por herramienta (Ripley, Kaneda, Spunkmeyer, Gaff, Daedalus, Sandbox)
a nivel global o específico por entrega.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import fnmatch
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Tuple
import yaml


@dataclass
class ToolChecksConfig:
    """Configuración de verificaciones de herramientas pedagógicas y estáticas."""

    # Ripley (P1 rules / AST)
    ripley_enabled: bool = True
    ripley_strict: bool = False
    ripley_rules: List[str] = field(default_factory=list)  # Vacío = todas las reglas
    ripley_disabled_rules: List[str] = field(default_factory=list)  # ej. ["0x0009h"]
    ripley_max_function_lines: int = 50
    ripley_max_line_length: int = 80

    # Kaneda / Seguridad
    kaneda_enabled: bool = True
    ban_dangerous_calls: bool = True  # ptrace, exec, sockets, system, popen
    ban_fork_bombs: bool = True
    ban_buffer_overflow_functions: bool = True  # gets, strcpy, sprintf, scanf sin ancho

    # Spunkmeyer / Antipatrones didácticos
    spunkmeyer_enabled: bool = True
    ban_feof_loop: bool = True
    ban_gets: bool = True
    ban_redundant_null_free: bool = True
    ban_dangling_stack_return: bool = True
    ban_redundant_boolean_comparison: bool = True
    ban_malloc_size_type: bool = True

    # Gaff / Linter de estilo
    gaff_enabled: bool = True
    enforce_snake_case: bool = True
    enforce_header_guards: bool = True
    ban_tab_indentation: bool = True
    enforce_variable_length: bool = True

    # Daedalus / Compilador
    daedalus_compiler: str = "esper"  # "esper", "gcc", "clang"
    compiler_flags: str = "-Wall -Wextra -std=c11"
    treat_warnings_as_errors: bool = False

    # Brett / Auditoría de Structs y Padding
    brett_enabled: bool = True
    audit_struct_padding: bool = True
    max_wasted_padding_bytes: int = 0

    # Bishop / Trazabilidad de Memoria
    bishop_enabled: bool = True
    detect_unfreed_allocations: bool = True

    # Drake / Fuzzing y Robustez
    drake_enabled: bool = True
    fuzz_boundary_limits: bool = True

    # Sandbox
    sandbox_memory_mb: int = 64
    sandbox_timeout_seconds: float = 5.0
    fail_on_memory_leak: bool = True
    fail_on_sanitizer: bool = True

    # Plagio / Winnowing
    plagiarism_threshold: float = 0.60
    plagiarism_strip_boilerplate: bool = True

    @classmethod
    def get_strict_preset(cls) -> ToolChecksConfig:
        """Retorna una configuración con el máximo nivel de rigurosidad pedagógica y estática."""
        return cls(
            ripley_enabled=True,
            ripley_strict=True,
            ripley_rules=["all"],
            ripley_disabled_rules=[],
            ripley_max_function_lines=40,
            ripley_max_line_length=80,
            kaneda_enabled=True,
            ban_dangerous_calls=True,
            ban_fork_bombs=True,
            ban_buffer_overflow_functions=True,
            spunkmeyer_enabled=True,
            ban_feof_loop=True,
            ban_gets=True,
            ban_redundant_null_free=True,
            ban_dangling_stack_return=True,
            ban_redundant_boolean_comparison=True,
            ban_malloc_size_type=True,
            gaff_enabled=True,
            enforce_snake_case=True,
            enforce_header_guards=True,
            ban_tab_indentation=True,
            enforce_variable_length=True,
            daedalus_compiler="esper",
            compiler_flags="-Wall -Wextra -Werror -pedantic -std=c11 -Wconversion -Wshadow -Wstrict-prototypes -Wmissing-prototypes -Wpointer-arith -Wcast-align -Wwrite-strings -fsanitize=address,undefined",
            treat_warnings_as_errors=True,
            brett_enabled=True,
            audit_struct_padding=True,
            max_wasted_padding_bytes=0,
            bishop_enabled=True,
            detect_unfreed_allocations=True,
            drake_enabled=True,
            fuzz_boundary_limits=True,
            sandbox_memory_mb=32,
            sandbox_timeout_seconds=3.0,
            fail_on_memory_leak=True,
            fail_on_sanitizer=True,
            plagiarism_threshold=0.55,
            plagiarism_strip_boilerplate=True,
        )

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ToolChecksConfig:
        if not data:
            return cls()

        ripley_data = data.get("ripley", {})
        kaneda_data = data.get("kaneda", {})
        spunk_data = data.get("spunkmeyer", {})
        gaff_data = data.get("gaff", {})
        daed_data = data.get("daedalus", {})
        brett_data = data.get("brett", {})
        bishop_data = data.get("bishop", {})
        drake_data = data.get("drake", {})
        sand_data = data.get("sandbox", {})
        plag_data = data.get("plagiarism", {})

        return cls(
            ripley_enabled=ripley_data.get("enabled", data.get("ripley_enabled", True)),
            ripley_strict=ripley_data.get("strict", data.get("ripley_strict", False)),
            ripley_rules=ripley_data.get("rules", data.get("ripley_rules", [])),
            ripley_disabled_rules=ripley_data.get("disabled_rules", data.get("ripley_disabled_rules", [])),
            ripley_max_function_lines=int(ripley_data.get("max_function_lines", 50)),
            ripley_max_line_length=int(ripley_data.get("max_line_length", 80)),
            kaneda_enabled=kaneda_data.get("enabled", data.get("kaneda_enabled", True)),
            ban_dangerous_calls=kaneda_data.get("ban_dangerous_calls", data.get("ban_dangerous_calls", True)),
            ban_fork_bombs=kaneda_data.get("ban_fork_bombs", data.get("ban_fork_bombs", True)),
            ban_buffer_overflow_functions=kaneda_data.get("ban_buffer_overflow_functions", True),
            spunkmeyer_enabled=spunk_data.get("enabled", data.get("spunkmeyer_enabled", True)),
            ban_feof_loop=spunk_data.get("ban_feof_loop", data.get("ban_feof_loop", True)),
            ban_gets=spunk_data.get("ban_gets", data.get("ban_gets", True)),
            ban_redundant_null_free=spunk_data.get("ban_redundant_null_free", True),
            ban_dangling_stack_return=spunk_data.get("ban_dangling_stack_return", True),
            ban_redundant_boolean_comparison=spunk_data.get("ban_redundant_boolean_comparison", True),
            ban_malloc_size_type=spunk_data.get("ban_malloc_size_type", True),
            gaff_enabled=gaff_data.get("enabled", data.get("gaff_enabled", True)),
            enforce_snake_case=gaff_data.get("enforce_snake_case", data.get("enforce_snake_case", True)),
            enforce_header_guards=gaff_data.get("enforce_header_guards", True),
            ban_tab_indentation=gaff_data.get("ban_tab_indentation", True),
            enforce_variable_length=gaff_data.get("enforce_variable_length", data.get("enforce_variable_length", True)),
            daedalus_compiler=daed_data.get("compiler", data.get("daedalus_compiler", "esper")),
            compiler_flags=daed_data.get("flags", data.get("compiler_flags", "-Wall -Wextra -std=c11")),
            treat_warnings_as_errors=daed_data.get("treat_warnings_as_errors", False),
            brett_enabled=brett_data.get("enabled", True),
            audit_struct_padding=brett_data.get("audit_struct_padding", True),
            max_wasted_padding_bytes=int(brett_data.get("max_wasted_padding_bytes", 0)),
            bishop_enabled=bishop_data.get("enabled", True),
            detect_unfreed_allocations=bishop_data.get("detect_unfreed_allocations", True),
            drake_enabled=drake_data.get("enabled", True),
            fuzz_boundary_limits=drake_data.get("fuzz_boundary_limits", True),
            sandbox_memory_mb=int(sand_data.get("max_memory_mb", data.get("sandbox_memory_mb", 64))),
            sandbox_timeout_seconds=float(sand_data.get("timeout_seconds", data.get("sandbox_timeout_seconds", 5.0))),
            fail_on_memory_leak=sand_data.get("fail_on_memory_leak", True),
            fail_on_sanitizer=sand_data.get("fail_on_sanitizer", True),
            plagiarism_threshold=float(plag_data.get("threshold", 0.60)),
            plagiarism_strip_boilerplate=plag_data.get("strip_boilerplate", True),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ripley": {
                "enabled": self.ripley_enabled,
                "strict": self.ripley_strict,
                "rules": self.ripley_rules,
                "disabled_rules": self.ripley_disabled_rules,
                "max_function_lines": self.ripley_max_function_lines,
                "max_line_length": self.ripley_max_line_length,
            },
            "daedalus": {
                "compiler": self.daedalus_compiler,
                "flags": self.compiler_flags,
                "treat_warnings_as_errors": self.treat_warnings_as_errors,
            },
            "kaneda": {
                "enabled": self.kaneda_enabled,
                "ban_dangerous_calls": self.ban_dangerous_calls,
                "ban_fork_bombs": self.ban_fork_bombs,
                "ban_buffer_overflow_functions": self.ban_buffer_overflow_functions,
            },
            "spunkmeyer": {
                "enabled": self.spunkmeyer_enabled,
                "ban_feof_loop": self.ban_feof_loop,
                "ban_gets": self.ban_gets,
                "ban_redundant_null_free": self.ban_redundant_null_free,
                "ban_dangling_stack_return": self.ban_dangling_stack_return,
                "ban_redundant_boolean_comparison": self.ban_redundant_boolean_comparison,
                "ban_malloc_size_type": self.ban_malloc_size_type,
            },
            "gaff": {
                "enabled": self.gaff_enabled,
                "enforce_snake_case": self.enforce_snake_case,
                "enforce_header_guards": self.enforce_header_guards,
                "ban_tab_indentation": self.ban_tab_indentation,
                "enforce_variable_length": self.enforce_variable_length,
            },
            "brett": {
                "enabled": self.brett_enabled,
                "audit_struct_padding": self.audit_struct_padding,
                "max_wasted_padding_bytes": self.max_wasted_padding_bytes,
            },
            "bishop": {
                "enabled": self.bishop_enabled,
                "detect_unfreed_allocations": self.detect_unfreed_allocations,
            },
            "drake": {
                "enabled": self.drake_enabled,
                "fuzz_boundary_limits": self.fuzz_boundary_limits,
            },
            "sandbox": {
                "max_memory_mb": self.sandbox_memory_mb,
                "timeout_seconds": self.sandbox_timeout_seconds,
                "fail_on_memory_leak": self.fail_on_memory_leak,
                "fail_on_sanitizer": self.fail_on_sanitizer,
            },
            "plagiarism": {
                "threshold": self.plagiarism_threshold,
                "strip_boilerplate": self.plagiarism_strip_boilerplate,
            },
        }


@dataclass
class MappingRule:
    zip_pattern: str
    entrega: str
    guia: Optional[str] = None
    titulo: str = ""
    descripcion: str = ""
    plantilla: Optional[str] = None
    checks: Optional[Dict[str, Any]] = None
    mode: Optional[str] = None  # "archivos_individuales", "makefile", "libreria", "proyecto", "auto"

    def matches_zip(self, zip_filename: str) -> bool:
        """Verifica si el nombre de archivo ZIP coincide con el patrón configurado."""
        name = Path(zip_filename).name
        if fnmatch.fnmatch(name.lower(), self.zip_pattern.lower()):
            return True
        pat_clean = self.zip_pattern.replace("*", "").strip()
        return bool(pat_clean and pat_clean.lower() in name.lower())

    def matches_activity(self, activity_slug: str) -> bool:
        """Verifica si el slug de actividad coincide con esta regla."""
        act_clean = activity_slug.strip("/\\").lower()
        ent_clean = self.entrega.strip("/\\").lower()
        return (
            act_clean == ent_clean
            or act_clean == ent_clean.replace("_", "-")
            or act_clean == ent_clean.replace("-", "_")
        )


@dataclass
class WorkspaceSettings:
    name: str = "Cátedra Programación 1"
    zips_dir: str = "zips"
    submissions_dir: str = "entregas"
    guias_dir: str = "guias"
    plantillas_dir: str = "plantillas"
    default_org: str = "INGCOM-UNRN-P1"
    default_mode: str = "auto"


@dataclass
class DreddConfig:
    workspace: WorkspaceSettings = field(default_factory=WorkspaceSettings)
    checks: ToolChecksConfig = field(default_factory=ToolChecksConfig)
    mapeos: List[MappingRule] = field(default_factory=list)
    raw_data: Dict[str, Any] = field(default_factory=dict)
    config_path: Optional[Path] = None

    def get_delivery_mode(
        self,
        activity_slug: Optional[str] = None,
        guide_mode: Optional[str] = None,
        target_path: Optional[Path] = None,
        cli_override: Optional[str] = None,
    ) -> str:
        """Determina el modo de entrega efectivo ('archivos_individuales' o 'makefile')
        aplicando la jerarquía de prioridad:
        1. CLI override explícito (si se proporcionó)
        2. dredd.yaml (regla de entrega puntual o global)
        3. Deckard guía (guia.tipo_entrega)
        4. Detección automática por presencia de Makefile
        5. Fallback por defecto ('archivos_individuales')
        """
        if cli_override and cli_override.lower() not in ("auto", "none", ""):
            return "makefile" if cli_override.lower() in ("make", "makefile", "proyecto", "libreria") else "archivos_individuales"

        if activity_slug:
            rule = self.find_mapping_for_activity(activity_slug)
            if rule and rule.mode and rule.mode.lower() not in ("auto", "none", ""):
                return "makefile" if rule.mode.lower() in ("make", "makefile", "proyecto", "libreria") else "archivos_individuales"

        if guide_mode and guide_mode.lower() not in ("auto", "none", ""):
            return "makefile" if guide_mode.lower() in ("make", "makefile", "proyecto", "libreria") else "archivos_individuales"

        if target_path and target_path.is_dir():
            if (target_path / "Makefile").is_file() or (target_path / "makefile").is_file():
                return "makefile"
            if list(target_path.glob("**/Makefile")) or list(target_path.glob("**/makefile")):
                return "makefile"

        return "archivos_individuales"

    def find_mapping_for_zip(self, zip_filename: str) -> Optional[MappingRule]:
        """Encuentra la primera regla de mapeo que coincida con el archivo ZIP."""
        for rule in self.mapeos:
            if rule.matches_zip(zip_filename):
                return rule
        return None

    def find_mapping_for_activity(self, activity_slug: str) -> Optional[MappingRule]:
        """Encuentra la regla de mapeo asociada a un slug de actividad."""
        for rule in self.mapeos:
            if rule.matches_activity(activity_slug):
                return rule
        return None

    def get_guide_path(self, activity_slug: str, base_dir: Optional[Path] = None) -> Optional[Path]:
        """Retorna la ruta resuelta hacia la guía de Deckard mapeada."""
        base = base_dir or (self.config_path.parent if self.config_path else Path.cwd())
        rule = self.find_mapping_for_activity(activity_slug)
        if rule and rule.guia:
            cand = base / rule.guia
            if cand.exists():
                return cand
            cand_alt = Path(rule.guia)
            if cand_alt.exists():
                return cand_alt
        return None

    def get_effective_checks(self, activity_slug: Optional[str] = None) -> ToolChecksConfig:
        """Calcula los chequeos efectivos fusionando las políticas globales con los overrides de la entrega."""
        global_dict = self.checks.to_dict()
        if not activity_slug:
            return self.checks

        rule = self.find_mapping_for_activity(activity_slug)
        if not rule or not rule.checks:
            return self.checks

        merged = dict(global_dict)
        for tool, tool_overrides in rule.checks.items():
            if isinstance(tool_overrides, dict) and tool in merged:
                merged[tool].update(tool_overrides)
            else:
                merged[tool] = tool_overrides

        return ToolChecksConfig.from_dict(merged)

    def add_or_update_mapping(self, rule: MappingRule) -> None:
        """Agrega o reemplaza una regla de mapeo según el slug de entrega."""
        for idx, existing in enumerate(self.mapeos):
            if existing.matches_activity(rule.entrega):
                self.mapeos[idx] = rule
                return
        self.mapeos.append(rule)

    def remove_mapping(self, activity_slug: str) -> bool:
        """Elimina una regla de mapeo según el slug de entrega."""
        initial_len = len(self.mapeos)
        self.mapeos = [m for m in self.mapeos if not m.matches_activity(activity_slug)]
        return len(self.mapeos) < initial_len

    def save(self, target_file: Optional[Path] = None) -> Path:
        """Guarda la configuración actual a archivo YAML."""
        out_path = target_file or self.config_path or (Path.cwd() / "dredd.yaml")
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(self.to_yaml(), encoding="utf-8")
        self.config_path = out_path
        return out_path

    def to_yaml(self) -> str:
        """Serializa la configuración a formato YAML estructurado."""
        mapeos_list = []
        for m in self.mapeos:
            item: Dict[str, Any] = {
                "zip_pattern": m.zip_pattern,
                "entrega": m.entrega,
                "guia": m.guia or "",
                "titulo": m.titulo or "",
            }
            if m.mode:
                item["mode"] = m.mode
            if m.descripcion:
                item["descripcion"] = m.descripcion
            if m.checks:
                item["checks"] = m.checks
            mapeos_list.append(item)

        data = {
            "version": "1.0",
            "workspace": {
                "name": self.workspace.name,
                "zips_dir": self.workspace.zips_dir,
                "submissions_dir": self.workspace.submissions_dir,
                "guias_dir": self.workspace.guias_dir,
                "plantillas_dir": self.workspace.plantillas_dir,
                "default_org": self.workspace.default_org,
                "default_mode": self.workspace.default_mode,
            },
            "checks": self.checks.to_dict(),
            "mapeos": mapeos_list,
        }
        return yaml.dump(data, sort_keys=False, allow_unicode=True)


def load_dredd_config(workspace_dir: Optional[Path | str] = None) -> Optional[DreddConfig]:
    """Carga dredd.yaml desde el workspace o directorios superiores."""
    start = Path(workspace_dir).resolve() if workspace_dir else Path.cwd().resolve()

    for p in [start] + list(start.parents)[:3]:
        for name in ("dredd.yaml", "dredd.yml", ".dredd.yaml"):
            cand = p / name
            if cand.is_file():
                try:
                    raw = yaml.safe_load(cand.read_text(encoding="utf-8")) or {}
                    ws_raw = raw.get("workspace", {})
                    ws = WorkspaceSettings(
                        name=ws_raw.get("name", "Cátedra Programación 1"),
                        zips_dir=ws_raw.get("zips_dir", "zips"),
                        submissions_dir=ws_raw.get("submissions_dir", "entregas"),
                        guias_dir=ws_raw.get("guias_dir", "guias"),
                        plantillas_dir=ws_raw.get("plantillas_dir", "plantillas"),
                        default_org=ws_raw.get("default_org", "INGCOM-UNRN-P1"),
                        default_mode=ws_raw.get("default_mode", "auto"),
                    )

                    checks_cfg = ToolChecksConfig.from_dict(raw.get("checks", {}))

                    mapeos = []
                    for m in raw.get("mapeos", []):
                        if isinstance(m, dict):
                            mapeos.append(
                                MappingRule(
                                    zip_pattern=m.get("zip_pattern", "*"),
                                    entrega=m.get("entrega", "entrega_1"),
                                    guia=m.get("guia"),
                                    titulo=m.get("titulo", ""),
                                    descripcion=m.get("descripcion", ""),
                                    plantilla=m.get("plantilla"),
                                    checks=m.get("checks"),
                                    mode=m.get("mode") or m.get("tipo_entrega"),
                                )
                            )
                    return DreddConfig(
                        workspace=ws,
                        checks=checks_cfg,
                        mapeos=mapeos,
                        raw_data=raw,
                        config_path=cand,
                    )
                except Exception:
                    pass

    return None


def init_workspace(
    target_dir: Path | str,
    name: str = "Cátedra Programación 1",
    zips_dir: str = "zips",
    submissions_dir: str = "entregas",
    guias_dir: str = "guias",
    plantillas_dir: str = "plantillas",
    force: bool = False,
) -> Tuple[Path, Path]:
    """Inicializa la estructura de carpetas y crea el archivo dredd.yaml con mapeos preconfigurados."""
    root = Path(target_dir).resolve()
    root.mkdir(parents=True, exist_ok=True)

    (root / zips_dir).mkdir(parents=True, exist_ok=True)
    (root / submissions_dir).mkdir(parents=True, exist_ok=True)
    (root / guias_dir).mkdir(parents=True, exist_ok=True)
    (root / plantillas_dir).mkdir(parents=True, exist_ok=True)

    header_path = root / plantillas_dir / "header.md"
    if not header_path.exists():
        header_path.write_text("# Informe de Corrección Docente · Cátedra Programación 1\n\n", encoding="utf-8")

    footer_path = root / plantillas_dir / "footer.md"
    if not footer_path.exists():
        footer_path.write_text(
            "\n---\n*Evaluación automatizada mediante Dredd y Ripley · Cátedra de Programación 1*\n",
            encoding="utf-8",
        )

    sample_guia_dir = root / guias_dir / "entrega_1"
    sample_guia_dir.mkdir(parents=True, exist_ok=True)
    sample_guia_yaml = sample_guia_dir / "guia.yaml"
    if not sample_guia_yaml.exists():
        sample_guia_content = """\
nombre: "Práctica 1 - Sintaxis, Variables y Control"
descripcion: "Guía práctica de ejercicios iniciales de Programación 1."
ejercicios:
  - id: "ejercicio1"
    titulo: "Suma de enteros y validación"
    tema: "Sintaxis básica"
    bloom: 2
  - id: "ejercicio2"
    titulo: "Cálculo de factorial y lazos"
    tema: "Estructuras de control"
    bloom: 3
"""
        sample_guia_yaml.write_text(sample_guia_content, encoding="utf-8")

    config_file = root / "dredd.yaml"
    if not config_file.exists() or force:
        cfg = DreddConfig(
            workspace=WorkspaceSettings(
                name=name,
                zips_dir=zips_dir,
                submissions_dir=submissions_dir,
                guias_dir=guias_dir,
                plantillas_dir=plantillas_dir,
            ),
            checks=ToolChecksConfig(
                ripley_enabled=True,
                ripley_strict=False,
                ripley_disabled_rules=[],
                kaneda_enabled=True,
                spunkmeyer_enabled=True,
                gaff_enabled=True,
                daedalus_compiler="esper",
                sandbox_memory_mb=64,
                sandbox_timeout_seconds=5.0,
            ),
            mapeos=[
                MappingRule(
                    zip_pattern="*entrega*1*.zip",
                    entrega="entrega_1",
                    guia=f"{guias_dir}/entrega_1/guia.yaml",
                    titulo="Práctica 1 - Sintaxis y Control",
                    checks={
                        "ripley": {"strict": False},
                        "sandbox": {"max_memory_mb": 64},
                    },
                ),
                MappingRule(
                    zip_pattern="*entrega*2*.zip",
                    entrega="entrega_2",
                    guia=f"{guias_dir}/entrega_2/guia.yaml",
                    titulo="Práctica 2 - Funciones y Punteros",
                ),
                MappingRule(
                    zip_pattern="*entrega*3*.zip",
                    entrega="entrega_3",
                    guia=f"{guias_dir}/entrega_3/guia.yaml",
                    titulo="Práctica 3 - Arrays, Strings y Structs",
                ),
            ],
            config_path=config_file,
        )
        config_file.write_text(cfg.to_yaml(), encoding="utf-8")

    return root, config_file


def validate_workspace(workspace_dir: Optional[Path | str] = None) -> List[Tuple[str, str, str]]:
    """Valida la integridad del espacio de trabajo y reporta problemas (nivel, componente, mensaje)."""
    ws = Path(workspace_dir).resolve() if workspace_dir else Path.cwd().resolve()
    cfg = load_dredd_config(ws)
    issues: List[Tuple[str, str, str]] = []

    if not cfg or not cfg.config_path:
        issues.append(("ERROR", "dredd.yaml", f"No se encontró dredd.yaml en {ws} ni en directorios padres."))
        return issues

    issues.append(("OK", "dredd.yaml", f"Archivo de configuración cargado desde {cfg.config_path}."))

    # Validar directorios del workspace
    for attr, dir_name in [
        ("Zips", cfg.workspace.zips_dir),
        ("Entregas", cfg.workspace.submissions_dir),
        ("Guías", cfg.workspace.guias_dir),
        ("Plantillas", cfg.workspace.plantillas_dir),
    ]:
        dp = ws / dir_name
        if not dp.exists():
            issues.append(("WARN", f"directorio:{attr}", f"El directorio '{dir_name}' no existe en {ws}."))
        else:
            issues.append(("OK", f"directorio:{attr}", f"Directorio '{dir_name}' presente."))

    # Validar mapeos y guías asociadas
    if not cfg.mapeos:
        issues.append(("WARN", "mapeos", "No hay entregas mapeadas en dredd.yaml."))
    else:
        for m in cfg.mapeos:
            if m.guia:
                gp = cfg.get_guide_path(m.entrega, ws)
                if not gp or not gp.exists():
                    issues.append(("WARN", f"guia:{m.entrega}", f"La guía '{m.guia}' para '{m.entrega}' no existe."))
                else:
                    issues.append(("OK", f"guia:{m.entrega}", f"Guía vinculada para '{m.entrega}': {m.guia}"))

    return issues
