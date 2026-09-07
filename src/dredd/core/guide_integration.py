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
    enunciado: str = ""
    pistas: List[str] = field(default_factory=list)

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
    enunciado: str = ""
    enunciado_path: Optional[Path] = None
    enunciado_source: str = ""

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


def _parse_ripkg_payload(ripkg_path: Path) -> Dict[str, Any]:
    """Extrae metadatos, consigna, pistas, casos de prueba y prototipos desde un paquete .ripkg."""
    import zipfile
    info: Dict[str, Any] = {
        "enunciado": "",
        "pistas": [],
        "test_cases": [],
        "functions": [],
        "starter_code": "",
        "tipo_entrega": None,
        "manifest": {},
    }
    if not ripkg_path.is_file():
        return info
    try:
        with zipfile.ZipFile(ripkg_path) as z:
            names = z.namelist()
            # 1. Manifest
            if "manifest.toml" in names:
                import tomllib
                try:
                    info["manifest"] = tomllib.loads(z.read("manifest.toml").decode("utf-8", errors="replace"))
                    info["tipo_entrega"] = info["manifest"].get("tipo_entrega") or info["manifest"].get("meta", {}).get("tipo_entrega")
                except Exception:
                    pass
            # 2. Enunciado / consigna
            for enunc_name in ["payload/enunciado.md", "enunciado.md", "payload/consigna.md", "consigna.md", "payload/README.md", "README.md"]:
                if enunc_name in names:
                    info["enunciado"] = z.read(enunc_name).decode("utf-8", errors="replace").strip()
                    break
            # 3. Pistas
            for p_name in ["payload/pistas.txt", "pistas.txt", "payload/pistas.md"]:
                if p_name in names:
                    raw_p = z.read(p_name).decode("utf-8", errors="replace").strip()
                    info["pistas"] = [line.strip() for line in raw_p.splitlines() if line.strip()]
                    break
            # 4. Tests .in / .out
            in_files = sorted([n for n in names if n.endswith(".in")])
            for in_f in in_files:
                stem = Path(in_f).stem
                parent = Path(in_f).parent
                out_candidate = str(parent / f"{stem}.out") if str(parent) != "." else f"{stem}.out"
                in_content = z.read(in_f).decode("utf-8", errors="replace")
                out_content = z.read(out_candidate).decode("utf-8", errors="replace") if out_candidate in names else ""
                info["test_cases"].append({
                    "nombre": stem,
                    "entrada": in_content,
                    "salida": out_content,
                })
            # 5. Funciones / headers
            h_c_files = [n for n in names if (n.endswith(".h") or n.endswith(".c")) and not n.endswith("prueba.c")]
            funcs = []
            for hf in h_c_files:
                code_text = z.read(hf).decode("utf-8", errors="replace")
                funcs.extend(extract_c_function_names(code_text))
                if not info["starter_code"] and hf.endswith(".h"):
                    info["starter_code"] = code_text
            info["functions"] = list(dict.fromkeys(funcs))
    except Exception:
        pass
    return info


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
        if not ex_dir and (gdir / "ejercicios" / eid).is_dir():
            ex_dir = gdir / "ejercicios" / eid
        if not ex_dir and (gdir / "libs" / eid).is_dir():
            ex_dir = gdir / "libs" / eid

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

        # 1. Chequeo de paquete .ripkg asociado al ejercicio / librería
        ripkg_file = None
        for cand_ripkg in [
            gdir / "ejercicios" / f"{eid}.ripkg",
            gdir / "libs" / f"{eid}.ripkg",
            gdir / f"{eid}.ripkg",
        ]:
            if cand_ripkg.is_file():
                ripkg_file = cand_ripkg
                break
        if not ripkg_file:
            matching_ripkgs = list(gdir.glob(f"**/{eid}.ripkg")) + list(gdir.glob(f"**/*{eid}*.ripkg"))
            if matching_ripkgs:
                ripkg_file = matching_ripkgs[0]

        ripkg_info = _parse_ripkg_payload(ripkg_file) if ripkg_file else {}
        ex_enunciado = ripkg_info.get("enunciado", "")
        ex_pistas = ripkg_info.get("pistas", [])
        if ripkg_info.get("test_cases"):
            test_cases = ripkg_info["test_cases"]
        if ripkg_info.get("tipo_entrega"):
            ej_tipo = ej_tipo or ripkg_info["tipo_entrega"]

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
                rol_familia = rol_familia or ej_data.get("rol_familia", ej_data.get("rol", item_data.get("role")))
                dependencias = dependencias or ej_data.get("dependencias", ej_data.get("requires", ej_data.get("deps", [])))
                archivos_req = archivos_req or ej_data.get("archivos_requeridos", ej_data.get("archivos_adicionales", []))
            except Exception:
                pass

        if ex_dir:
            tests_dir = ex_dir / "tests"
            if tests_dir.is_dir() and not test_cases:
                for f_in in sorted(tests_dir.glob("*.in")):
                    f_out = tests_dir / f"{f_in.stem}.out"
                    test_cases.append({
                        "nombre": f_in.stem,
                        "entrada": f_in.read_text(encoding="utf-8", errors="replace"),
                        "salida": f_out.read_text(encoding="utf-8", errors="replace") if f_out.is_file() else "",
                    })
            if not ex_enunciado:
                for cand_en in [ex_dir / "enunciado.md", ex_dir / "consigna.md", ex_dir / "README.md"]:
                    if cand_en.is_file():
                        ex_enunciado = cand_en.read_text(encoding="utf-8", errors="replace").strip()
                        break

        funcs = extract_c_function_names(starter) + extract_c_function_names(solucion) + ripkg_info.get("functions", [])

        exercises.append(
            GuideExercise(
                id=eid,
                titulo=titulo,
                tema=tema,
                bloom=int(bloom) if str(bloom).isdigit() else 1,
                tags=tags,
                starter_code=starter or ripkg_info.get("starter_code", ""),
                solucion_c=solucion,
                test_cases=test_cases,
                exercise_dir=ex_dir,
                functions=list(dict.fromkeys(funcs)),
                tipo_entrega=ej_tipo,
                familia=familia,
                rol_familia=rol_familia,
                dependencias=dependencias if isinstance(dependencias, list) else [dependencias],
                archivos_requeridos=archivos_req if isinstance(archivos_req, list) else [archivos_req],
                enunciado=ex_enunciado,
                pistas=ex_pistas,
            )
        )

    guide_tipo_global = data.get("tipo_entrega", data.get("build_mode", "archivos_individuales"))
    familias_global = data.get("familias", list(dict.fromkeys(e.familia for e in exercises if e.familia)))

    # Buscar enunciado general de la guía / práctica
    general_enunciado = ""
    general_enunciado_path = None
    for enunc_cand in [
        gdir / "enunciado.md",
        gdir / "consigna.md",
        gdir / "guia.md",
        gdir / "README.md",
        gdir.parent / "enunciado.md",
        gdir.parent / "consigna.md",
        gdir.parent / "README.md",
    ]:
        if enunc_cand.is_file():
            general_enunciado = enunc_cand.read_text(encoding="utf-8", errors="replace").strip()
            general_enunciado_path = enunc_cand
            break

    return ActivityGuide(
        nombre=nombre,
        guide_dir=gdir,
        exercises=exercises,
        raw_meta=data,
        tipo_entrega=guide_tipo_global,
        familias=familias_global,
        enunciado=general_enunciado,
        enunciado_path=general_enunciado_path,
        enunciado_source=str(gdir),
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
        ex_enunciado = ""

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

        for cand_en in [ed / "enunciado.md", ed / "consigna.md", ed / "README.md"]:
            if cand_en.is_file():
                ex_enunciado = cand_en.read_text(encoding="utf-8", errors="replace").strip()
                break

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
                enunciado=ex_enunciado,
            )
        )

    general_enunciado = ""
    general_path = None
    for cand_en in [guide_dir / "enunciado.md", guide_dir / "consigna.md", guide_dir / "README.md", guide_dir.parent / "README.md"]:
        if cand_en.is_file():
            general_enunciado = cand_en.read_text(encoding="utf-8", errors="replace").strip()
            general_path = cand_en
            break

    return ActivityGuide(
        nombre=guide_dir.name.replace("_", " ").title(),
        guide_dir=guide_dir,
        exercises=exercises,
        tipo_entrega="archivos_individuales",
        enunciado=general_enunciado,
        enunciado_path=general_path,
        enunciado_source=str(guide_dir),
    )


def load_guide_from_deckard_dir(deckard_dir: Path) -> Optional[ActivityGuide]:
    """Carga una guía y sus enunciados desde un directorio .deckard (máxima prioridad)."""
    if not deckard_dir.is_dir():
        return None

    # 1. Buscar guia.yaml o guia.yml en .deckard
    for gy_name in ("guia.yaml", "guia.yml"):
        gy = deckard_dir / gy_name
        if gy.is_file():
            guide = _parse_guide_yaml_file(gy, guide_dir=deckard_dir)
            if guide:
                guide.enunciado_source = f".deckard ({deckard_dir})"
                return guide

    # 2. Descubrir .ripkgs directamente en .deckard o subdirectorios
    ripkgs = (
        sorted(deckard_dir.glob("*.ripkg"))
        + sorted(deckard_dir.glob("ejercicios/*.ripkg"))
        + sorted(deckard_dir.glob("libs/*.ripkg"))
    )
    if ripkgs:
        exercises: List[GuideExercise] = []
        for rp in ripkgs:
            eid = rp.stem
            info = _parse_ripkg_payload(rp)
            exercises.append(
                GuideExercise(
                    id=eid,
                    titulo=eid.replace("-", " ").replace("_", " ").title(),
                    tema="general",
                    bloom=1,
                    starter_code=info.get("starter_code", ""),
                    test_cases=info.get("test_cases", []),
                    functions=info.get("functions", []),
                    tipo_entrega=info.get("tipo_entrega") or "archivos_individuales",
                    enunciado=info.get("enunciado", ""),
                    pistas=info.get("pistas", []),
                )
            )
        general_enunciado = ""
        general_path = None
        for enunc_cand in [
            deckard_dir / "enunciado.md",
            deckard_dir / "consigna.md",
            deckard_dir / "README.md",
            deckard_dir.parent / "enunciado.md",
            deckard_dir.parent / "consigna.md",
            deckard_dir.parent / "README.md",
        ]:
            if enunc_cand.is_file():
                general_enunciado = enunc_cand.read_text(encoding="utf-8", errors="replace").strip()
                general_path = enunc_cand
                break
        return ActivityGuide(
            nombre=deckard_dir.parent.name.replace("_", " ").title(),
            guide_dir=deckard_dir,
            exercises=exercises,
            tipo_entrega="archivos_individuales",
            enunciado=general_enunciado,
            enunciado_path=general_path,
            enunciado_source=f".deckard ({deckard_dir})",
        )

    # 3. Subdirectorios con ejercicio.yaml
    sub_ejs = [d for d in deckard_dir.iterdir() if d.is_dir() and (d / "ejercicio.yaml").is_file()]
    if sub_ejs:
        g = _parse_guide_from_exercise_dirs(deckard_dir, sub_ejs)
        g.enunciado_source = f".deckard ({deckard_dir})"
        return g

    return None


def load_activity_guide(
    submissions_dir: Path | str,
    activity_slug: str,
    workspace_dir: Optional[Path | str] = None,
) -> Optional[ActivityGuide]:
    """Busca y carga el enunciado y la guía de una práctica de programación.

    Prioridad de búsqueda estricta:
    1. PRIORIDAD MÁXIMA: Directorio '.deckard' local en la práctica o entrega:
       - En el directorio de entregas/práctica (sub_dir / ".deckard")
       - En subdirectorios del slug (sub_dir / clean_slug / ".deckard")
       - En cualquier subdirectorio de primer nivel que contenga '.deckard' (ej. TP1-2026/TP1-2026/.deckard)
       - En el workspace (ws / ".deckard")
       - En el directorio actual de trabajo (CWD / ".deckard")
    2. CONFIGURACIÓN GENERAL (si .deckard no está presente):
       - Mapeo declarativo en dredd.yaml (cfg.get_guide_path)
       - Directorios canónicos de prácticas:
         * /home/mrtin/dev/p1/practicas/2026/<clean_slug>
         * /home/mrtin/dev/p1/practicas/*/<clean_slug>
         * <workspace>/practicas/<clean_slug>
         * <workspace>/guias/<clean_slug>
         * <workspace>/guias/<clean_slug>/guia.yaml
         * <sub_dir>/guia o <sub_dir>/guia.yaml
    """
    sub_dir = Path(submissions_dir).resolve() if submissions_dir else Path.cwd()
    ws = Path(workspace_dir).resolve() if workspace_dir else Path.cwd()
    clean_slug = Path(activity_slug).name.rstrip("/\\") or activity_slug.strip("/\\")

    # =========================================================================
    # 1. PRIORIDAD MÁXIMA: Buscar en directorio '.deckard'
    # =========================================================================
    deckard_candidates = [
        sub_dir / ".deckard",
        sub_dir / clean_slug / ".deckard",
        ws / ".deckard",
        Path.cwd() / ".deckard",
    ]

    # Subcarpetas inmediatas de sub_dir que posean .deckard (ej. sub_dir/TP1-2026/.deckard)
    if sub_dir.is_dir():
        try:
            for child in sub_dir.iterdir():
                if child.is_dir() and not child.name.startswith("."):
                    deck_child = child / ".deckard"
                    if deck_child.is_dir() and deck_child not in deckard_candidates:
                        deckard_candidates.append(deck_child)
        except Exception:
            pass

    for cand_deck in deckard_candidates:
        if cand_deck.is_dir():
            g = load_guide_from_deckard_dir(cand_deck)
            if g:
                g.enunciado_source = f".deckard ({cand_deck})"
                return g

    # =========================================================================
    # 2. CONFIGURACIÓN GENERAL: Fallback si .deckard no está presente
    # =========================================================================
    from dredd.core.config import load_dredd_config
    cfg = load_dredd_config(ws) or load_dredd_config(sub_dir)

    # 2a. dredd.yaml mapeo
    if cfg:
        cfg_guide_path = cfg.get_guide_path(clean_slug, ws)
        if cfg_guide_path:
            if cfg_guide_path.is_file() and cfg_guide_path.suffix in (".yaml", ".yml"):
                g = _parse_guide_yaml_file(cfg_guide_path)
                if g:
                    g.enunciado_source = f"configuración general (dredd.yaml: {cfg_guide_path})"
                    return g
            elif cfg_guide_path.is_dir():
                # Si el directorio configurado en dredd.yaml tiene .deckard, usarlo
                for deck_sub in [cfg_guide_path / ".deckard", cfg_guide_path / clean_slug / ".deckard"]:
                    if deck_sub.is_dir():
                        g = load_guide_from_deckard_dir(deck_sub)
                        if g:
                            g.enunciado_source = f"configuración general (.deckard en {deck_sub})"
                            return g
                gy = cfg_guide_path / "guia.yaml" if (cfg_guide_path / "guia.yaml").is_file() else cfg_guide_path / "guia.yml"
                if gy.is_file():
                    g = _parse_guide_yaml_file(gy, guide_dir=cfg_guide_path)
                    if g:
                        g.enunciado_source = f"configuración general ({cfg_guide_path})"
                        return g

    # 2b. Directorios estándar y rutas canónicas de prácticas (ej. /home/mrtin/dev/p1/practicas/2026/TP1-2026)
    general_locations: List[Path] = []

    # Rutas canónicas en el sistema
    practicas_base = Path("/home/mrtin/dev/p1/practicas")
    if practicas_base.is_dir():
        general_locations.append(practicas_base / "2026" / clean_slug)
        try:
            for year_dir in practicas_base.iterdir():
                if year_dir.is_dir() and year_dir.name != "2026":
                    general_locations.append(year_dir / clean_slug)
        except Exception:
            pass

    # Rutas configuradas en workspace
    if cfg and getattr(cfg.workspace, "practicas_dir", None):
        general_locations.append(ws / cfg.workspace.practicas_dir / clean_slug)

    general_locations.extend([
        sub_dir / "guia",
        sub_dir / "guia.yaml",
        sub_dir / "guia.yml",
        sub_dir / "guide",
        ws / "guias" / clean_slug / "guia.yaml",
        ws / "guias" / clean_slug,
        ws / "guias" / f"{clean_slug}.yaml",
        ws / "guias" / f"{clean_slug}.yml",
        ws / "guia",
    ])

    for cand in general_locations:
        if cand.is_file() and cand.suffix in (".yaml", ".yml"):
            g = _parse_guide_yaml_file(cand)
            if g:
                g.enunciado_source = f"configuración general ({cand})"
                return g
        elif cand.is_dir():
            # Si el directorio de la práctica tiene .deckard (directo o anidado)
            for cand_deck in [cand / ".deckard", cand / clean_slug / ".deckard"]:
                if cand_deck.is_dir():
                    g = load_guide_from_deckard_dir(cand_deck)
                    if g:
                        g.enunciado_source = f"configuración general ({cand_deck})"
                        return g
            try:
                for sub in cand.iterdir():
                    if sub.is_dir() and (sub / ".deckard").is_dir():
                        g = load_guide_from_deckard_dir(sub / ".deckard")
                        if g:
                            g.enunciado_source = f"configuración general ({sub / '.deckard'})"
                            return g
            except Exception:
                pass

            guide_yaml = cand / "guia.yaml" if (cand / "guia.yaml").is_file() else cand / "guia.yml"
            if guide_yaml.is_file():
                g = _parse_guide_yaml_file(guide_yaml, guide_dir=cand)
                if g:
                    g.enunciado_source = f"configuración general ({cand})"
                    return g

            try:
                sub_ejs = [d for d in cand.iterdir() if d.is_dir() and (d / "ejercicio.yaml").is_file()]
                if sub_ejs:
                    g = _parse_guide_from_exercise_dirs(cand, sub_ejs)
                    g.enunciado_source = f"configuración general ({cand})"
                    return g
            except Exception:
                pass

    return None
