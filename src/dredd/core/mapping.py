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


def heuristic_match(filename: str, available_exercises: List[str]) -> Optional[str]:
    """Infiere el ejercicio correspondiente a partir del nombre del archivo C."""
    if not available_exercises:
        return None

    stem = Path(filename).stem.lower().strip()

    # 1. Coincidencia exacta
    for ex in available_exercises:
        if stem == ex.lower():
            return ex

    # 2. Extracción de dígitos
    file_digits = re.findall(r"\d+", stem)
    if file_digits:
        target_num = file_digits[-1]
        matching_exercises = [
            ex for ex in available_exercises if target_num in re.findall(r"\d+", ex)
        ]
        if len(matching_exercises) == 1:
            return matching_exercises[0]

    # 3. Coincidencia de subcadena única
    substring_matches = [
        ex for ex in available_exercises if ex.lower() in stem or stem in ex.lower()
    ]
    if len(substring_matches) == 1:
        return substring_matches[0]

    # Si hay un solo ejercicio disponible y es main.c o tp.c
    if len(available_exercises) == 1 and stem in ("main", "tp", "tarea", "entrega", "programa"):
        return available_exercises[0]

    return None


class MappingStore:
    """Administra la persistencia de los mapeos de archivos en mappings.json."""

    def __init__(self, workspace_dir: str | Path, activity_slug: str) -> None:
        self.workspace_dir = Path(workspace_dir)
        self.activity_slug = activity_slug
        self.mapping_file = self.workspace_dir / activity_slug / "mappings.json"
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
    ) -> Optional[str]:
        if student_slug in self.config.student_mappings:
            if filename in self.config.student_mappings[student_slug]:
                return self.config.student_mappings[student_slug][filename]

        if filename in self.config.global_mappings:
            return self.config.global_mappings[filename]

        return heuristic_match(filename, available_exercises)

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
    ) -> None:
        self.workspace_dir = Path(workspace_dir)
        self.activity_slug = activity_slug
        self.console = console or Console()
        self.store = MappingStore(workspace_dir, activity_slug)

    def collect_all_student_files(
        self,
        available_exercises: List[str],
    ) -> List[FileMappingEntry]:
        activity_dir = self.workspace_dir / self.activity_slug
        if not activity_dir.exists():
            return []

        entries: List[FileMappingEntry] = []

        for s_dir in sorted(activity_dir.iterdir()):
            if not s_dir.is_dir() or s_dir.name.startswith("."):
                continue

            rev_dirs = [d for d in s_dir.iterdir() if d.is_dir() and re.match(r"^r\d+$", d.name)]
            if not rev_dirs:
                # Si no tiene revisiones rN, buscar directo en el directorio
                c_files = sorted(s_dir.glob("*.c"))
            else:
                latest_rev = sorted(rev_dirs, key=lambda d: int(d.name[1:]))[-1]
                c_files = sorted(latest_rev.glob("*.c"))

            for c_file in c_files:
                effective = self.store.get_effective_mapping(
                    s_dir.name, c_file.name, available_exercises
                )
                detected = heuristic_match(c_file.name, available_exercises)
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
                if entry.current_mapping is None and entry.detected_exercise:
                    self.store.set_global_mapping(entry.filename, entry.detected_exercise)
                    entry.current_mapping = entry.detected_exercise
                    entry.is_ambiguous_or_unmapped = False
                    changes_count += 1

        to_review = [e for e in entries if e.is_ambiguous_or_unmapped] if unmapped_only else entries
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
