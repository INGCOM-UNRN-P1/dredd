"""Moodle zip batch ingestion, encoding normalization, flattening, and SHA-256 versioning."""

from dataclasses import dataclass, field
import hashlib
import io
from pathlib import Path
import re
import tarfile
from typing import Dict, List, Optional, Tuple
import zipfile

from slugify import slugify

from dredd.core.db import DatabaseManager, StudentRecord

ALLOWED_EXTENSIONS = {".c", ".h", ".mk", ".md", ".txt"}
ALLOWED_FILENAMES = {"makefile", "cmakelists.txt"}
IGNORED_PARTS = {"__macosx", ".ds_store", ".git", ".vscode", ".idea"}


def is_ignored(path_str: str) -> bool:
    """Verifica si una ruta contiene componentes que deban descartarse."""
    p = Path(path_str)
    if any(part.lower() in IGNORED_PARTS for part in p.parts) or p.name.startswith("."):
        return True
    return False


def is_allowed_file(rel_path_str: str) -> bool:
    """Valida si un archivo es admisible como código o configuración del proyecto."""
    if is_ignored(rel_path_str):
        return False
    p = Path(rel_path_str)
    if p.name.lower() in ALLOWED_FILENAMES:
        return True
    return p.suffix.lower() in ALLOWED_EXTENSIONS


PROTECTED_ROOT_DIRS = {"ejercicios", "src", "lib", "test", "tests"}


def is_protected_dir(name: str) -> bool:
    """Evita descartar directorios semánticos de código o de ejercicios."""
    nl = name.lower()
    if nl in PROTECTED_ROOT_DIRS:
        return True
    if re.match(r"^ej(?:ercicio)?_?\d+", nl):
        return True
    return False


def _get_common_root_prefix(names: List[str]) -> str:
    """Calcula de forma iterativa el prefijo común de carpetas envolventes."""
    valid_names = [n for n in names if not is_ignored(n)]
    if not valid_names:
        return ""

    prefix = ""
    while True:
        current_names = [n[len(prefix):] for n in valid_names]
        parts_list = [n.split("/") for n in current_names]
        if all(len(p) > 1 for p in parts_list):
            roots = {p[0] for p in parts_list}
            if len(roots) == 1:
                root = list(roots)[0]
                if is_protected_dir(root):
                    break
                prefix += root + "/"
                continue
        break
    return prefix


def extract_archive_payload(
    raw_bytes: bytes,
    binary_collector: Optional[List[Tuple[str, str]]] = None,
    base_prefix: str = "",
    depth: int = 0,
) -> List[Tuple[str, bytes]]:
    """Extrae archivos permitidos de un ZIP o TAR en memoria normalizando barras, jerarquías y descomprimiendo recursivamente."""
    if depth > 10:
        return []

    from dredd.core.binary_check import is_binary_file

    raw_files: Dict[str, bytes] = {}

    # 1. Probar como ZIP
    if zipfile.is_zipfile(io.BytesIO(raw_bytes)):
        try:
            with zipfile.ZipFile(io.BytesIO(raw_bytes)) as z:
                entry_map: List[Tuple[str, str]] = []
                for orig_name in z.namelist():
                    norm_name = orig_name.replace("\\", "/")
                    if not norm_name.endswith("/"):
                        entry_map.append((orig_name, norm_name))

                names = [norm_name for _, norm_name in entry_map]
                strip_prefix = _get_common_root_prefix(names)

                for orig_name, norm_name in entry_map:
                    rel = (
                        norm_name[len(strip_prefix):]
                        if strip_prefix and norm_name.startswith(strip_prefix)
                        else norm_name
                    )
                    full_rel = f"{base_prefix}/{rel}".strip("/") if base_prefix else rel.strip("/")

                    if is_ignored(full_rel):
                        continue

                    try:
                        file_bytes = z.read(orig_name)
                    except Exception:
                        continue

                    ext = Path(full_rel).suffix.lower()
                    if ext in (".zip", ".tar", ".gz", ".tgz") or zipfile.is_zipfile(io.BytesIO(file_bytes[:1024])):
                        inner_base = str(Path(full_rel).parent)
                        if inner_base == ".":
                            inner_base = ""
                        nested_res = extract_archive_payload(
                            file_bytes,
                            binary_collector=binary_collector,
                            base_prefix=inner_base,
                            depth=depth + 1,
                        )
                        for n_path, n_bytes in nested_res:
                            raw_files[n_path] = n_bytes
                    else:
                        is_bin, bin_reason = is_binary_file(full_rel, file_bytes[:1024])
                        if is_bin:
                            if binary_collector is not None:
                                binary_collector.append((full_rel, bin_reason))
                            continue
                        if is_allowed_file(full_rel):
                            raw_files[full_rel] = file_bytes
            return list(raw_files.items())
        except Exception:
            pass

    # 2. Fallback: Probar como TAR (caso Iriarte)
    try:
        if tarfile.is_tarfile(io.BytesIO(raw_bytes)):
            with tarfile.open(fileobj=io.BytesIO(raw_bytes)) as tf:
                members = [m for m in tf.getmembers() if m.isfile()]
                names = [m.name.replace("\\", "/") for m in members]
                strip_prefix = _get_common_root_prefix(names)
                for m, norm_name in zip(members, names):
                    rel = (
                        norm_name[len(strip_prefix):]
                        if strip_prefix and norm_name.startswith(strip_prefix)
                        else norm_name
                    )
                    full_rel = f"{base_prefix}/{rel}".strip("/") if base_prefix else rel.strip("/")

                    if is_ignored(full_rel):
                        continue

                    f = tf.extractfile(m)
                    if not f:
                        continue
                    file_bytes = f.read()

                    ext = Path(full_rel).suffix.lower()
                    if ext in (".zip", ".tar", ".gz", ".tgz"):
                        inner_base = str(Path(full_rel).parent)
                        if inner_base == ".":
                            inner_base = ""
                        nested_res = extract_archive_payload(
                            file_bytes,
                            binary_collector=binary_collector,
                            base_prefix=inner_base,
                            depth=depth + 1,
                        )
                        for n_path, n_bytes in nested_res:
                            raw_files[n_path] = n_bytes
                    else:
                        is_bin, bin_reason = is_binary_file(full_rel, file_bytes[:1024])
                        if is_bin:
                            if binary_collector is not None:
                                binary_collector.append((full_rel, bin_reason))
                            continue
                        if is_allowed_file(full_rel):
                            raw_files[full_rel] = file_bytes
            return list(raw_files.items())
    except Exception:
        pass

    return list(raw_files.items())


@dataclass
class ParsedMoodleZip:
    activity_name: str
    activity_id: str
    activity_slug: str
    is_unknown_activity: bool = False
    config_created_or_updated: bool = False
    warning_message: str = ""


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
        force: bool = False,
    ) -> Tuple[ParsedMoodleZip, List[IngestionResult]]:
        zip_file_path = Path(zip_path)
        if not zip_file_path.exists():
            raise FileNotFoundError(f"El archivo ZIP no existe: {zip_file_path}")

        moodle_info = parse_moodle_zip_filename(zip_file_path)

        # Verificar si hay regla de mapeo en dredd.yaml
        from dredd.core.config import load_dredd_config
        cfg = load_dredd_config(self.workspace_dir)
        rule = (cfg.find_mapping_for_zip(zip_file_path.name) or cfg.find_mapping_for_activity(moodle_info.activity_slug)) if cfg else None

        if rule:
            moodle_info.activity_slug = rule.entrega
            if rule.titulo:
                moodle_info.activity_name = rule.titulo
            sub_dir_name = cfg.workspace.submissions_dir if cfg else ""
            if sub_dir_name and (self.workspace_dir / sub_dir_name).is_dir():
                activity_dir = self.workspace_dir / sub_dir_name / rule.entrega
            else:
                activity_dir = self.workspace_dir / rule.entrega
        else:
            moodle_info.is_unknown_activity = True
            cfg_file = (cfg.config_path if cfg and cfg.config_path else (self.workspace_dir / "dredd.yaml"))

            clean_act = re.sub(r"[^a-zA-Z0-9]+", "*", moodle_info.activity_name.lower()).strip("*")
            zip_pat = f"*{clean_act}*.zip" if clean_act else f"*{zip_file_path.name}"

            from dredd.core.config import DreddConfig, WorkspaceSettings, ToolChecksConfig, MappingRule
            if cfg is None:
                cfg = DreddConfig(
                    workspace=WorkspaceSettings(),
                    checks=ToolChecksConfig(),
                    mapeos=[],
                    config_path=cfg_file,
                )

            guias_dir = cfg.workspace.guias_dir or "guias"
            skeleton_rule = MappingRule(
                zip_pattern=zip_pat,
                entrega=moodle_info.activity_slug,
                guia=f"{guias_dir}/{moodle_info.activity_slug}/guia.yaml",
                titulo=moodle_info.activity_name,
                descripcion="Configuración autogenerada para práctica desconocida. Debe ser ajustada.",
                mode="archivos_individuales",
            )
            cfg.add_or_update_mapping(skeleton_rule)

            if not dry_run:
                cfg.save(cfg_file)
                moodle_info.config_created_or_updated = True

            moodle_info.warning_message = (
                f"Práctica desconocida '{moodle_info.activity_name}' detectada. "
                f"Se creó un esqueleto de configuración en '{cfg_file}' que debe ser ajustado."
            )

            sub_dir_name = cfg.workspace.submissions_dir if cfg else ""
            if sub_dir_name and (self.workspace_dir / sub_dir_name).is_dir():
                activity_dir = self.workspace_dir / sub_dir_name / moodle_info.activity_slug
            else:
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
                binary_collector: List[Tuple[str, str]] = []

                for fpath in file_paths:
                    filename = Path(fpath).name
                    ext = Path(filename).suffix.lower()
                    raw_content = zf.read(fpath)

                    # Verificar si el archivo en sí es un binario directo
                    from dredd.core.binary_check import is_binary_file
                    is_bin, bin_reason = is_binary_file(filename, raw_content[:1024])
                    if is_bin and ext not in (".zip", ".tar", ".gz", ".tgz"):
                        ignored.append(
                            IgnoredFileInfo(
                                filename=filename,
                                reason=f"ERROR_BINARY: {bin_reason}",
                            )
                        )
                        continue

                    # Si es archivo comprimido (zip, tar, o bytes de zip/tar), extraer su contenido respetando jerarquías
                    if ext in (".zip", ".tar", ".gz", ".tgz") or zipfile.is_zipfile(io.BytesIO(raw_content)) or tarfile.is_tarfile(io.BytesIO(raw_content)):
                        archived_files = extract_archive_payload(raw_content, binary_collector=binary_collector)
                        if archived_files:
                            for rel_path, file_bytes in archived_files:
                                text, _ = normalize_encoding(file_bytes)
                                utf8_bytes = text.encode("utf-8")
                                sha256 = hashlib.sha256(utf8_bytes).hexdigest()
                                sources.append(
                                    ProcessedSourceFile(
                                        filename=rel_path,
                                        content=utf8_bytes,
                                        sha256=sha256,
                                        size_bytes=len(utf8_bytes),
                                    )
                                )
                        elif not binary_collector:
                            ignored.append(
                                IgnoredFileInfo(
                                    filename=filename,
                                    reason="Archivo comprimido sin fuentes válidos o formato no soportado",
                                )
                            )
                    elif is_allowed_file(fpath):
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
                                reason=f"Extensión o archivo no permitido '{ext}'",
                            )
                        )

                # Registrar los binarios filtrados del alumno para auditoría docente
                for bin_file, bin_reason in binary_collector:
                    ignored.append(
                        IgnoredFileInfo(
                            filename=bin_file,
                            reason=f"ERROR_BINARY: {bin_reason}",
                        )
                    )

                combined_hash = calculate_sources_hash(sources)
                student_dir = activity_dir / parsed_student.student_slug
                db_path = student_dir / ".metadata.db"

                if not dry_run:
                    if force and student_dir.exists():
                        import shutil
                        shutil.rmtree(student_dir, ignore_errors=True)

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
                        rev_folder_name = f"r{next_version}"
                        rev_dir = student_dir / rev_folder_name
                        rev_dir.mkdir(parents=True, exist_ok=True)

                        for src in sources:
                            dest = rev_dir / src.filename
                            dest.parent.mkdir(parents=True, exist_ok=True)
                            dest.write_bytes(src.content)

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
