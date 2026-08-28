"""Moodle zip batch ingestion, encoding normalization, flattening, and SHA-256 versioning."""

from dataclasses import dataclass, field
import hashlib
from pathlib import Path
import re
from typing import Dict, List, Optional, Tuple
import zipfile

from slugify import slugify

from dredd.core.db import DatabaseManager, StudentRecord

ALLOWED_EXTENSIONS = {".c", ".h"}


@dataclass
class ParsedMoodleZip:
    activity_name: str
    activity_id: str
    activity_slug: str


@dataclass
class ParsedStudentEntry:
    raw_name: str
    student_name: str
    student_id: str
    submission_id: str
    student_slug: str


@dataclass
class ProcessedSourceFile:
    filename: str
    content: bytes
    sha256: str
    size_bytes: int


@dataclass
class IgnoredFileInfo:
    filename: str
    reason: str


@dataclass
class IngestionResult:
    student_slug: str
    student_name: str
    version_created: Optional[int]
    is_new_revision: bool
    sources: List[ProcessedSourceFile] = field(default_factory=list)
    ignored: List[IgnoredFileInfo] = field(default_factory=list)


def parse_moodle_zip_filename(zip_path: str | Path) -> ParsedMoodleZip:
    """Parsea el nombre del archivo ZIP de Moodle extrayendo nombre de actividad e ID."""
    filename = Path(zip_path).name
    match = re.search(r"(?:^|.*?-)([^-\n]+)-(\d+)\.zip$", filename, re.IGNORECASE)
    if match:
        raw_act_name = match.group(1).strip()
        act_id = match.group(2).strip()
    else:
        base = Path(filename).stem
        parts = base.split("-") if "-" in base else base.split("_")
        if len(parts) >= 2 and parts[-1].isdigit():
            raw_act_name = "-".join(parts[:-1]).strip()
            act_id = parts[-1].strip()
        else:
            raw_act_name = base
            act_id = "0"

    act_slug_name = slugify(raw_act_name)
    act_slug = f"{act_slug_name}_{act_id}" if act_id != "0" else act_slug_name
    return ParsedMoodleZip(
        activity_name=raw_act_name,
        activity_id=act_id,
        activity_slug=act_slug,
    )


def parse_student_folder_name(folder_name: str) -> Optional[ParsedStudentEntry]:
    """Parsea el nombre de la carpeta de entrega de un estudiante en Moodle."""
    clean_name = folder_name.strip("/\\")
    match = re.match(
        r"^([^_]+)_(\d+)_assignsubmission_(?:file|onlinetext)?.*$", clean_name, re.IGNORECASE
    )
    if match:
        student_name = match.group(1).strip()
        submission_id = match.group(2).strip()
    else:
        parts = clean_name.split("_")
        student_name = parts[0].strip()
        submission_id = parts[1].strip() if len(parts) > 1 and parts[1].isdigit() else "0"

    student_slug = f"{slugify(student_name)}_{submission_id}"
    return ParsedStudentEntry(
        raw_name=clean_name,
        student_name=student_name,
        student_id=submission_id,
        submission_id=submission_id,
        student_slug=student_slug,
    )


def normalize_encoding(raw_bytes: bytes) -> Tuple[str, str]:
    """Detecta y normaliza el encoding del archivo a texto UTF-8."""
    try:
        return raw_bytes.decode("utf-8"), "utf-8"
    except UnicodeDecodeError:
        pass

    try:
        return raw_bytes.decode("utf-8-sig"), "utf-8-sig"
    except UnicodeDecodeError:
        pass

    encodings_to_try = [
        "windows-1252",
        "cp1252",
        "iso-8859-1",
        "latin-1",
        "mac_roman",
    ]

    for enc in encodings_to_try:
        try:
            text = raw_bytes.decode(enc)
            return text, enc
        except (UnicodeDecodeError, LookupError):
            continue

    return raw_bytes.decode("utf-8", errors="replace"), "utf-8 (fallback)"


def calculate_sources_hash(sources: List[ProcessedSourceFile]) -> str:
    """Calcula un hash SHA-256 determinista sobre los archivos fuente ordenados."""
    hasher = hashlib.sha256()
    for src in sorted(sources, key=lambda s: s.filename):
        hasher.update(f"{src.filename}:{src.sha256}\n".encode("utf-8"))
    return hasher.hexdigest()


class MoodleIngestor:
    """Procesa e ingesta lotes ZIP de Moodle con sanitización y versionado."""

    def __init__(self, workspace_dir: str | Path = ".") -> None:
        self.workspace_dir = Path(workspace_dir)

    def process_zip(
        self,
        zip_path: str | Path,
        dry_run: bool = False,
    ) -> Tuple[ParsedMoodleZip, List[IngestionResult]]:
        zip_file_path = Path(zip_path)
        if not zip_file_path.exists():
            raise FileNotFoundError(f"El archivo ZIP no existe: {zip_file_path}")

        moodle_info = parse_moodle_zip_filename(zip_file_path)
        activity_dir = self.workspace_dir / moodle_info.activity_slug

        with zipfile.ZipFile(zip_file_path, "r") as zf:
            namelist = zf.namelist()
            student_entries: Dict[str, List[str]] = {}

            for item in namelist:
                if item.endswith("/"):
                    continue
                parts = item.split("/")
                root_folder = parts[0]
                if root_folder not in student_entries:
                    student_entries[root_folder] = []
                student_entries[root_folder].append(item)

            results: List[IngestionResult] = []

            for root_folder, file_paths in student_entries.items():
                parsed_student = parse_student_folder_name(root_folder)
                if not parsed_student:
                    continue

                sources: List[ProcessedSourceFile] = []
                ignored: List[IgnoredFileInfo] = []

                for fpath in file_paths:
                    filename = Path(fpath).name
                    ext = Path(filename).suffix.lower()
                    raw_content = zf.read(fpath)

                    if ext in ALLOWED_EXTENSIONS:
                        text, _ = normalize_encoding(raw_content)
                        utf8_bytes = text.encode("utf-8")
                        sha256 = hashlib.sha256(utf8_bytes).hexdigest()
                        sources.append(
                            ProcessedSourceFile(
                                filename=filename,
                                content=utf8_bytes,
                                sha256=sha256,
                                size_bytes=len(utf8_bytes),
                            )
                        )
                    else:
                        ignored.append(
                            IgnoredFileInfo(
                                filename=filename,
                                reason=f"Extensión no permitida '{ext}'",
                            )
                        )

                combined_hash = calculate_sources_hash(sources)
                student_dir = activity_dir / parsed_student.student_slug
                db_path = student_dir / ".metadata.db"

                if not dry_run:
                    student_dir.mkdir(parents=True, exist_ok=True)
                    db = DatabaseManager(db_path)
                    db.upsert_student(
                        StudentRecord(
                            student_id=parsed_student.student_id,
                            full_name=parsed_student.student_name,
                            slug=parsed_student.student_slug,
                            submission_id=parsed_student.submission_id,
                        )
                    )
                    latest_rev = db.get_latest_revision(parsed_student.student_slug)

                    is_new = True
                    next_version = 1

                    if latest_rev:
                        if latest_rev["sources_hash"] == combined_hash:
                            is_new = False
                            next_version = latest_rev["version_num"]
                        else:
                            next_version = latest_rev["version_num"] + 1

                    if is_new:
                        rev_folder_name = f"r{next_version}_f"
                        rev_dir = student_dir / rev_folder_name
                        rev_dir.mkdir(parents=True, exist_ok=True)

                        for src in sources:
                            (rev_dir / src.filename).write_bytes(src.content)

                        db.add_revision(
                            student_slug=parsed_student.student_slug,
                            version_num=next_version,
                            sources_hash=combined_hash,
                            folder_path=str(rev_dir),
                            sources=[
                                {
                                    "filename": s.filename,
                                    "file_hash": s.sha256,
                                    "size_bytes": s.size_bytes,
                                }
                                for s in sources
                            ],
                            ignored=[
                                {"filename": ign.filename, "reason": ign.reason} for ign in ignored
                            ],
                        )

                    results.append(
                        IngestionResult(
                            student_slug=parsed_student.student_slug,
                            student_name=parsed_student.student_name,
                            version_created=next_version if is_new else None,
                            is_new_revision=is_new,
                            sources=sources,
                            ignored=ignored,
                        )
                    )
                else:
                    results.append(
                        IngestionResult(
                            student_slug=parsed_student.student_slug,
                            student_name=parsed_student.student_name,
                            version_created=1,
                            is_new_revision=True,
                            sources=sources,
                            ignored=ignored,
                        )
                    )

            return moodle_info, results
