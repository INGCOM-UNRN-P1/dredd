"""Integración entre Dredd y las guías / especificaciones de Deckard."""

from dataclasses import dataclass, field
from pathlib import Path
import re
from typing import Any, Dict, List, Optional
import yaml


@dataclass
class GuideExercise:
    id: str
    titulo: str = ""
    tema: str = ""
    bloom: int = 1
    tags: List[str] = field(default_factory=list)
    starter_code: str = ""
    solucion_c: str = ""
    test_cases: List[Dict[str, Any]] = field(default_factory=list)
    exercise_dir: Optional[Path] = None
    functions: List[str] = field(default_factory=list)
    tipo_entrega: str = "archivos_individuales"
    familia: Optional[str] = None
    rol_familia: Optional[str] = None  # "libreria", "tests", "uso", "app"
    dependencias: List[str] = field(default_factory=list)
    archivos_requeridos: List[str] = field(default_factory=list)

    @property
    def display_name(self) -> str:
        suffix = f" [{self.familia}:{self.rol_familia}]" if self.familia and self.rol_familia else ""
        return f"{self.id} ({self.titulo}){suffix}" if self.titulo else f"{self.id}{suffix}"


@dataclass
class ActivityGuide:
    nombre: str
    guide_dir: Path
    exercises: List[GuideExercise] = field(default_factory=list)
    raw_meta: Dict[str, Any] = field(default_factory=dict)
    tipo_entrega: str = "archivos_individuales"
    familias: List[str] = field(default_factory=list)

    def get_exercise(self, ex_id: str) -> Optional[GuideExercise]:
        for e in self.exercises:
            if e.id == ex_id:
                return e
        return None

    def get_exercise_ids(self) -> List[str]:
        return [e.id for e in self.exercises]

    def get_family_exercises(self, family_name: str) -> List[GuideExercise]:
        return [e for e in self.exercises if (e.familia or "").lower() == family_name.lower()]

    def get_exercises_by_role(self, role: str) -> List[GuideExercise]:
        return [e for e in self.exercises if (e.rol_familia or "").lower() == role.lower()]


def extract_c_function_names(c_code: str) -> List[str]:
    """Extrae nombres de funciones declaradas o definidas en código C."""
    if not c_code:
        return []
    pattern = r"\b(?:[a-zA-Z_][a-zA-Z0-9_*]*\s+)+([a-zA-Z_][a-zA-Z0-9_]*)\s*\([^)]*\)"
    matches = re.findall(pattern, c_code)
    keywords = {"if", "while", "for", "switch", "return", "sizeof", "typedef", "struct", "void", "int", "char", "float", "double"}
    return [m for m in matches if m not in keywords]


def _parse_guide_yaml_file(yaml_path: Path, guide_dir: Optional[Path] = None) -> Optional[ActivityGuide]:
    try:
        data = yaml.safe_load(yaml_path.read_text(encoding="utf-8")) or {}
    except Exception:
        return None

    gdir = guide_dir or yaml_path.parent
    nombre = data.get("nombre", data.get("titulo", gdir.name.replace("_", " ").title()))
    raw_ejs = data.get("ejercicios", [])

    exercises: List[GuideExercise] = []

    for idx, item in enumerate(raw_ejs):
        if isinstance(item, str):
            eid = item
            item_data = {}
        elif isinstance(item, dict):
            eid = item.get("id", f"ejercicio{idx+1}")
            item_data = item
        else:
            continue

        ex_dir = gdir / eid if (gdir / eid).is_dir() else None
        ej_yaml = ex_dir / "ejercicio.yaml" if ex_dir else None

        titulo = item_data.get("titulo", "")
        tema = item_data.get("tema", "")
        bloom = item_data.get("bloom", 1)
        tags = item_data.get("tags", [])
        starter = item_data.get("starter_code", "")
        solucion = item_data.get("solucion_c", "")
        test_cases = []

        guide_tipo = data.get("tipo_entrega", data.get("build_mode", "archivos_individuales"))
        ej_tipo = item_data.get("tipo_entrega", item_data.get("build_mode", guide_tipo))
        familia = item_data.get("familia", item_data.get("family"))
        rol_familia = item_data.get("rol_familia", item_data.get("rol", item_data.get("role")))
        dependencias = item_data.get("dependencias", item_data.get("requires", item_data.get("deps", [])))
        archivos_req = item_data.get("archivos_requeridos", item_data.get("archivos_adicionales", []))

        if ej_yaml and ej_yaml.is_file():
            try:
                ej_data = yaml.safe_load(ej_yaml.read_text(encoding="utf-8")) or {}
                titulo = titulo or ej_data.get("titulo", "")
                tema = tema or ej_data.get("tema", "")
                bloom = bloom or ej_data.get("bloom", 1)
                tags = tags or ej_data.get("tags", [])
                starter = starter or ej_data.get("starter_code", "")
                solucion = solucion or ej_data.get("solucion_c", "")
                ej_tipo = ej_data.get("tipo_entrega", ej_data.get("build_mode", ej_tipo))
                familia = familia or ej_data.get("familia", ej_data.get("family"))
                rol_familia = rol_familia or ej_data.get("rol_familia", ej_data.get("rol", ej_data.get("role")))
                dependencias = dependencias or ej_data.get("dependencias", ej_data.get("requires", ej_data.get("deps", [])))
                archivos_req = archivos_req or ej_data.get("archivos_requeridos", ej_data.get("archivos_adicionales", []))
            except Exception:
                pass

        if ex_dir:
            tests_dir = ex_dir / "tests"
            if tests_dir.is_dir():
                for f_in in sorted(tests_dir.glob("*.in")):
                    f_out = tests_dir / f"{f_in.stem}.out"
                    test_cases.append({
                        "nombre": f_in.stem,
                        "entrada": f_in.read_text(encoding="utf-8", errors="replace"),
                        "salida": f_out.read_text(encoding="utf-8", errors="replace") if f_out.is_file() else "",
                    })

        funcs = extract_c_function_names(starter) + extract_c_function_names(solucion)

        exercises.append(
            GuideExercise(
                id=eid,
                titulo=titulo,
                tema=tema,
                bloom=int(bloom) if str(bloom).isdigit() else 1,
                tags=tags,
                starter_code=starter,
                solucion_c=solucion,
                test_cases=test_cases,
                exercise_dir=ex_dir,
                functions=list(dict.fromkeys(funcs)),
                tipo_entrega=ej_tipo,
                familia=familia,
                rol_familia=rol_familia,
                dependencias=dependencias if isinstance(dependencias, list) else [dependencias],
                archivos_requeridos=archivos_req if isinstance(archivos_req, list) else [archivos_req],
            )
        )

    guide_tipo_global = data.get("tipo_entrega", data.get("build_mode", "archivos_individuales"))
    familias_global = data.get("familias", list(dict.fromkeys(e.familia for e in exercises if e.familia)))
    return ActivityGuide(
        nombre=nombre,
        guide_dir=gdir,
        exercises=exercises,
        raw_meta=data,
        tipo_entrega=guide_tipo_global,
        familias=familias_global,
    )


def _parse_guide_from_exercise_dirs(guide_dir: Path, exercise_dirs: List[Path]) -> ActivityGuide:
    exercises: List[GuideExercise] = []
    for ed in sorted(exercise_dirs):
        ej_yaml = ed / "ejercicio.yaml"
        titulo = ed.name
        tema = "general"
        bloom = 1
        tags = []
        starter = ""
        solucion = ""
        ej_tipo = "archivos_individuales"

        if ej_yaml.is_file():
            try:
                ej_data = yaml.safe_load(ej_yaml.read_text(encoding="utf-8")) or {}
                titulo = ej_data.get("titulo", titulo)
                tema = ej_data.get("tema", tema)
                bloom = ej_data.get("bloom", bloom)
                tags = ej_data.get("tags", tags)
                starter = ej_data.get("starter_code", starter)
                solucion = ej_data.get("solucion_c", solucion)
                ej_tipo = ej_data.get("tipo_entrega", ej_data.get("build_mode", ej_tipo))
            except Exception:
                pass

        test_cases = []
        tests_dir = ed / "tests"
        if tests_dir.is_dir():
            for f_in in sorted(tests_dir.glob("*.in")):
                f_out = tests_dir / f"{f_in.stem}.out"
                test_cases.append({
                    "nombre": f_in.stem,
                    "entrada": f_in.read_text(encoding="utf-8", errors="replace"),
                    "salida": f_out.read_text(encoding="utf-8", errors="replace") if f_out.is_file() else "",
                })

        funcs = extract_c_function_names(starter) + extract_c_function_names(solucion)
        exercises.append(
            GuideExercise(
                id=ed.name,
                titulo=titulo,
                tema=tema,
                bloom=int(bloom) if str(bloom).isdigit() else 1,
                tags=tags,
                starter_code=starter,
                solucion_c=solucion,
                test_cases=test_cases,
                exercise_dir=ed,
                functions=list(dict.fromkeys(funcs)),
                tipo_entrega=ej_tipo,
            )
        )

    return ActivityGuide(
        nombre=guide_dir.name.replace("_", " ").title(),
        guide_dir=guide_dir,
        exercises=exercises,
        tipo_entrega="archivos_individuales",
    )


def load_activity_guide(
    submissions_dir: Path | str,
    activity_slug: str,
    workspace_dir: Optional[Path | str] = None,
) -> Optional[ActivityGuide]:
    """Busca y carga la guía de Deckard asociada a la actividad.

    Prioridad de búsqueda:
    1. Subdirectorio 'guia/' dentro de submissions_dir (ej. entrega-3_1238305/guia/)
    2. Archivo 'guia.yaml' / 'guia.yml' dentro de submissions_dir
    3. Directorio 'guias/<activity_slug>' en el workspace
    4. Directorio 'guia/' en el workspace
    """
    sub_dir = Path(submissions_dir).resolve() if submissions_dir else Path.cwd()
    ws = Path(workspace_dir).resolve() if workspace_dir else Path.cwd()

    clean_slug = Path(activity_slug).name.rstrip("/\\") or activity_slug.strip("/\\")

    # 0. Mapeo declarativo en dredd.yaml
    from dredd.core.config import load_dredd_config
    cfg = load_dredd_config(ws) or load_dredd_config(sub_dir)
    if cfg:
        cfg_guide_path = cfg.get_guide_path(clean_slug, ws)
        if cfg_guide_path:
            if cfg_guide_path.is_file() and cfg_guide_path.suffix in (".yaml", ".yml"):
                g = _parse_guide_yaml_file(cfg_guide_path)
                if g:
                    return g
            elif cfg_guide_path.is_dir():
                gy = cfg_guide_path / "guia.yaml" if (cfg_guide_path / "guia.yaml").is_file() else cfg_guide_path / "guia.yml"
                if gy.is_file():
                    g = _parse_guide_yaml_file(gy, guide_dir=cfg_guide_path)
                    if g:
                        return g

    candidate_locations = [
        sub_dir / "guia",
        sub_dir / "guia.yaml",
        sub_dir / "guia.yml",
        sub_dir / "guide",
        ws / "guias" / clean_slug / "guia.yaml",
        ws / "guias" / clean_slug,
        ws / "guias" / f"{clean_slug}.yaml",
        ws / "guias" / f"{clean_slug}.yml",
        ws / "guia",
    ]

    for cand in candidate_locations:
        if cand.is_file() and cand.suffix in (".yaml", ".yml"):
            g = _parse_guide_yaml_file(cand)
            if g:
                return g
        elif cand.is_dir():
            guide_yaml = cand / "guia.yaml"
            if not guide_yaml.is_file():
                guide_yaml = cand / "guia.yml"
            if guide_yaml.is_file():
                g = _parse_guide_yaml_file(guide_yaml, guide_dir=cand)
                if g:
                    return g

            sub_ejs = [d for d in cand.iterdir() if d.is_dir() and (d / "ejercicio.yaml").is_file()]
            if sub_ejs:
                return _parse_guide_from_exercise_dirs(cand, sub_ejs)

    return None
