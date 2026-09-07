"""Módulo interactivo y heurístico de mapeo entre archivos fuente C y ejercicios."""

from dataclasses import dataclass, field
import json
from pathlib import Path
import re
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.syntax import Syntax

from dredd.core.guide_integration import ActivityGuide, load_activity_guide

SPECIAL_AUXILIARY = "[AUXILIAR]"
SPECIAL_IGNORE = "[IGNORAR]"


@dataclass
class FileMappingEntry:
    student_slug: str
    filename: str
    file_path: Path
    detected_exercise: Optional[str]
    current_mapping: Optional[str]
    is_ambiguous_or_unmapped: bool


@dataclass
class ActivityMappingConfig:
    activity_slug: str
    global_mappings: Dict[str, str] = field(default_factory=dict)
    student_mappings: Dict[str, Dict[str, str]] = field(default_factory=dict)


def heuristic_match(
    filename: str,
    available_exercises: List[str],
    file_content: Optional[str] = None,
    guide: Optional[ActivityGuide] = None,
) -> Optional[str]:
    """Infiere el ejercicio correspondiente a partir del nombre del archivo C, su contenido y la guía de Deckard."""
    if not available_exercises:
        return None

    stem = Path(filename).stem.lower().strip()

    # 1. Coincidencia exacta de ID
    for ex in available_exercises:
        ex_clean = ex.lower()
        if stem == ex_clean or stem.replace("-", "_") == ex_clean.replace("-", "_"):
            return ex

    # 2. Si tenemos la guía de Deckard vinculada, cotejar funciones, títulos y orden
    if guide:
        # Cotejo por funciones declaradas / definidas en el archivo C
        if file_content:
            for ex_obj in guide.exercises:
                if ex_obj.id in available_exercises:
                    for fn in ex_obj.functions:
                        if fn and re.search(r"\b" + re.escape(fn) + r"\b", file_content):
                            return ex_obj.id

        # Cotejo por palabras clave en título del ejercicio
        for ex_obj in guide.exercises:
            if ex_obj.id in available_exercises and ex_obj.titulo:
                palabras = [w.lower() for w in re.findall(r"\w+", ex_obj.titulo) if len(w) >= 4]
                for p in palabras:
                    if p in stem or stem in p or (len(p) >= 4 and len(stem) >= 4 and p[:4] == stem[:4]):
                        return ex_obj.id

        # Cotejo posicional: ej1 / ejercicio1 -> 1er ejercicio de la guía
        file_digits = re.findall(r"\d+", stem)
        if file_digits:
            num = int(file_digits[-1])
            if 1 <= num <= len(guide.exercises):
                cand_id = guide.exercises[num - 1].id
                if cand_id in available_exercises:
                    return cand_id

    # 3. Extracción de dígitos respecto a ejercicios disponibles
    file_digits = re.findall(r"\d+", stem)
    if file_digits:
        target_num = file_digits[-1]
        matching_exercises = [
            ex for ex in available_exercises if target_num in re.findall(r"\d+", ex)
        ]
        if len(matching_exercises) == 1:
            return matching_exercises[0]

    # 4. Coincidencia de subcadena única
    clean_stem = stem.replace("-", "").replace("_", "")
    substring_matches = [
        ex for ex in available_exercises
        if ex.lower().replace("-", "").replace("_", "") in clean_stem or clean_stem in ex.lower().replace("-", "").replace("_", "")
    ]
    if len(substring_matches) == 1:
        return substring_matches[0]

    # 5. Si hay un solo ejercicio disponible y el archivo es genérico
    if len(available_exercises) == 1 and stem in ("main", "tp", "tarea", "entrega", "programa", "codigo", "solution"):
        return available_exercises[0]

    return None


class MappingStore:
    """Administra la persistencia de los mapeos de archivos en mappings.json."""

    def __init__(
        self,
        workspace_dir: str | Path,
        activity_slug: str,
        mapping_file: Optional[Path] = None,
    ) -> None:
        self.workspace_dir = Path(workspace_dir)
        self.activity_slug = activity_slug
        self.mapping_file = mapping_file or (self.workspace_dir / activity_slug / "mappings.json")
        self.config = self.load()

    def load(self) -> ActivityMappingConfig:
        if not self.mapping_file.exists():
            return ActivityMappingConfig(activity_slug=self.activity_slug)

        try:
            data = json.loads(self.mapping_file.read_text(encoding="utf-8"))
            return ActivityMappingConfig(
                activity_slug=data.get("activity_slug", self.activity_slug),
                global_mappings=data.get("global_mappings", {}),
                student_mappings=data.get("student_mappings", {}),
            )
        except Exception:
            return ActivityMappingConfig(activity_slug=self.activity_slug)

    def save(self) -> None:
        self.mapping_file.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "activity_slug": self.config.activity_slug,
            "global_mappings": self.config.global_mappings,
            "student_mappings": self.config.student_mappings,
        }
        self.mapping_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    def get_effective_mapping(
        self,
        student_slug: str,
        filename: str,
        available_exercises: List[str],
        file_content: Optional[str] = None,
        guide: Optional[ActivityGuide] = None,
    ) -> Optional[str]:
        if student_slug in self.config.student_mappings:
            if filename in self.config.student_mappings[student_slug]:
                return self.config.student_mappings[student_slug][filename]

        if filename in self.config.global_mappings:
            return self.config.global_mappings[filename]

        return heuristic_match(filename, available_exercises, file_content=file_content, guide=guide)

    def set_student_mapping(self, student_slug: str, filename: str, target: str) -> None:
        if student_slug not in self.config.student_mappings:
            self.config.student_mappings[student_slug] = {}
        self.config.student_mappings[student_slug][filename] = target

    def set_global_mapping(self, filename: str, target: str) -> None:
        self.config.global_mappings[filename] = target


class InteractiveMapper:
    """Herramienta interactiva para revisar y configurar mapeos entre archivos y testcases."""

    def __init__(
        self,
        workspace_dir: str | Path,
        activity_slug: str,
        console: Optional[Console] = None,
        submissions_dir: Optional[Path] = None,
    ) -> None:
        self.workspace_dir = Path(workspace_dir)
        self.activity_slug = activity_slug
        self.console = console or Console()
        self.submissions_dir = submissions_dir

        target_dir = self.submissions_dir or (self.workspace_dir / self.activity_slug)
        mapping_file = target_dir / "mappings.json"
        self.store = MappingStore(self.workspace_dir, self.activity_slug, mapping_file=mapping_file)
        self.guide = load_activity_guide(target_dir, self.activity_slug, self.workspace_dir)

    def collect_all_student_files(
        self,
        available_exercises: List[str],
    ) -> List[FileMappingEntry]:
        activity_dir = self.submissions_dir or (self.workspace_dir / self.activity_slug)
        if not activity_dir.exists():
            return []

        entries: List[FileMappingEntry] = []

        for s_dir in sorted(activity_dir.iterdir()):
            if not s_dir.is_dir() or s_dir.name.startswith((".", "_")) or s_dir.name in ("guia", "guide", "templates", "informe", "baseline", "_baseline"):
                continue

            rev_dirs = [d for d in s_dir.iterdir() if d.is_dir() and re.match(r"^r\d+$", d.name)]
            if not rev_dirs:
                # Si no tiene revisiones rN, buscar directo en el directorio
                c_files = sorted(s_dir.glob("*.c"))
            else:
                latest_rev = sorted(rev_dirs, key=lambda d: int(d.name[1:]))[-1]
                c_files = sorted(latest_rev.glob("*.c"))

            for c_file in c_files:
                file_text = None
                try:
                    file_text = c_file.read_text(encoding="utf-8", errors="ignore")
                except Exception:
                    pass

                effective = self.store.get_effective_mapping(
                    s_dir.name, c_file.name, available_exercises, file_content=file_text, guide=self.guide
                )
                detected = heuristic_match(c_file.name, available_exercises, file_content=file_text, guide=self.guide)
                is_unmapped = effective is None

                entries.append(
                    FileMappingEntry(
                        student_slug=s_dir.name,
                        filename=c_file.name,
                        file_path=c_file,
                        detected_exercise=detected,
                        current_mapping=effective,
                        is_ambiguous_or_unmapped=is_unmapped,
                    )
                )

        return entries

    def run_interactive_session(
        self,
        available_exercises: List[str],
        unmapped_only: bool = False,
        auto_apply: bool = False,
        prompt_fn: Optional[Callable[[str], str]] = None,
    ) -> int:
        entries = self.collect_all_student_files(available_exercises)
        if not entries:
            self.console.print("[yellow]No se encontraron archivos .c para mapear.[/yellow]")
            return 0

        changes_count = 0
        if auto_apply:
            for entry in entries:
                if entry.detected_exercise and entry.filename not in self.store.config.global_mappings:
                    self.store.set_global_mapping(entry.filename, entry.detected_exercise)
                    entry.current_mapping = entry.detected_exercise
                    entry.is_ambiguous_or_unmapped = False
                    changes_count += 1

        to_review = [e for e in entries if e.is_ambiguous_or_unmapped] if (unmapped_only or auto_apply) else entries
        if not to_review:
            self.console.print("[bold green]✓ Todos los archivos ya están correctamente vinculados.[/bold green]")
            if changes_count > 0:
                self.store.save()
            return changes_count

        options_list = list(available_exercises) + [SPECIAL_AUXILIARY, SPECIAL_IGNORE]

        for idx, entry in enumerate(to_review, start=1):
            self.console.print(f"\n[bold magenta]─── Archivo {idx}/{len(to_review)} ───[/bold magenta]")
            self.console.print(f"Estudiante: [cyan]{entry.student_slug}[/cyan]")
            self.console.print(f"Archivo:    [bold yellow]{entry.filename}[/bold yellow]")
            self.console.print(f"Estado:     {entry.current_mapping or '[red]Sin vincular[/red]'}")

            for opt_idx, opt in enumerate(options_list, start=1):
                self.console.print(f"  [bold cyan]{opt_idx})[/bold cyan] {opt}")
            self.console.print("  [bold yellow]s)[/bold yellow] Saltar")
            self.console.print("  [bold red]q)[/bold red] Guardar y Salir")

            prompt_text = "Seleccioná una opción"
            choice = prompt_fn(prompt_text).strip() if prompt_fn else Prompt.ask(prompt_text, default="s").strip()

            if choice.lower() == "q":
                break
            elif choice.lower() == "s":
                continue

            if choice.isdigit():
                num = int(choice)
                if 1 <= num <= len(options_list):
                    selected = options_list[num - 1]
                    self.store.set_global_mapping(entry.filename, selected)
                    entry.current_mapping = selected
                    entry.is_ambiguous_or_unmapped = False
                    changes_count += 1

        self.store.save()
        return changes_count
