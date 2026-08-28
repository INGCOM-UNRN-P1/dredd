"""Gestión de configuración declarativa del espacio de trabajo de Dredd (dredd.yaml)."""

from __future__ import annotations

from dataclasses import dataclass, field
import fnmatch
from pathlib import Path
import re
from typing import Any, Dict, List, Optional
import yaml


@dataclass
class MappingRule:
    zip_pattern: str
    entrega: str
    guia: Optional[str] = None
    titulo: str = ""
    descripcion: str = ""
    plantilla: Optional[str] = None

    def matches_zip(self, zip_filename: str) -> bool:
        """Verifica si el nombre de archivo ZIP coincide con el patrón configurado."""
        name = Path(zip_filename).name
        if fnmatch.fnmatch(name.lower(), self.zip_pattern.lower()):
            return True
        # Coincidencia exacta o por substring
        pat_clean = self.zip_pattern.replace("*", "").strip()
        return bool(pat_clean and pat_clean.lower() in name.lower())

    def matches_activity(self, activity_slug: str) -> bool:
        """Verifica si el slug de actividad coincide con esta regla."""
        act_clean = activity_slug.strip("/\\").lower()
        ent_clean = self.entrega.strip("/\\").lower()
        return act_clean == ent_clean or act_clean == ent_clean.replace("_", "-") or act_clean == ent_clean.replace("-", "_")


@dataclass
class WorkspaceSettings:
    name: str = "Cátedra Programación 1"
    zips_dir: str = "zips"
    submissions_dir: str = "entregas"
    guias_dir: str = "guias"
    plantillas_dir: str = "plantillas"
    default_org: str = "INGCOM-UNRN-P1"


@dataclass
class DreddConfig:
    workspace: WorkspaceSettings = field(default_factory=WorkspaceSettings)
    mapeos: List[MappingRule] = field(default_factory=list)
    raw_data: Dict[str, Any] = field(default_factory=dict)
    config_path: Optional[Path] = None

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
        """Retorna la ruta absoluta o resuelta hacia la guía de Deckard mapeada."""
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

    def to_yaml(self) -> str:
        """Serializa la configuración a formato YAML legible."""
        data = {
            "version": "1.0",
            "workspace": {
                "name": self.workspace.name,
                "zips_dir": self.workspace.zips_dir,
                "submissions_dir": self.workspace.submissions_dir,
                "guias_dir": self.workspace.guias_dir,
                "plantillas_dir": self.workspace.plantillas_dir,
                "default_org": self.workspace.default_org,
            },
            "mapeos": [
                {
                    "zip_pattern": m.zip_pattern,
                    "entrega": m.entrega,
                    "guia": m.guia or "",
                    "titulo": m.titulo or "",
                }
                for m in self.mapeos
            ],
        }
        return yaml.dump(data, sort_keys=False, allow_unicode=True)


def load_dredd_config(workspace_dir: Optional[Path | str] = None) -> Optional[DreddConfig]:
    """Carga dredd.yaml desde el workspace o directorios superiores."""
    start = Path(workspace_dir).resolve() if workspace_dir else Path.cwd().resolve()
    
    candidates = [
        start / "dredd.yaml",
        start / "dredd.yml",
        start / ".dredd.yaml",
        start / ".dredd.yml",
    ]

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
                    )
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
                                )
                            )
                    return DreddConfig(
                        workspace=ws,
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

    # Crear directorios estructurados
    (root / zips_dir).mkdir(parents=True, exist_ok=True)
    (root / submissions_dir).mkdir(parents=True, exist_ok=True)
    (root / guias_dir).mkdir(parents=True, exist_ok=True)
    (root / plantillas_dir).mkdir(parents=True, exist_ok=True)

    # Plantillas de informe por defecto
    header_path = root / plantillas_dir / "header.md"
    if not header_path.exists():
        header_path.write_text("# Informe de Corrección Docente · Cátedra Programación 1\n\n", encoding="utf-8")

    footer_path = root / plantillas_dir / "footer.md"
    if not footer_path.exists():
        footer_path.write_text(
            "\n---\n*Evaluación automatizada mediante Dredd y Ripley · Cátedra de Programación 1*\n",
            encoding="utf-8",
        )

    # Guía de ejemplo para la entrega 1
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
            mapeos=[
                MappingRule(
                    zip_pattern="*entrega*1*.zip",
                    entrega="entrega_1",
                    guia=f"{guias_dir}/entrega_1/guia.yaml",
                    titulo="Práctica 1 - Sintaxis y Control",
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
