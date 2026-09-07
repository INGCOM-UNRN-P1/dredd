"""Ingesta de archivos ZIP de Moodle y exportación de planillas de calificaciones."""

import csv
from pathlib import Path
import re
import shutil
from typing import Dict, List
import zipfile


def unpack_moodle_zip(zip_path: Path, exercise: str, workspace_dir: Path) -> List[str]:
    """Descomprime un archivo ZIP masivo de Moodle en <workspace>/<exercise>-submissions/<estudiante>/."""
    submissions_dir = workspace_dir / f"{exercise}-submissions"
    submissions_dir.mkdir(parents=True, exist_ok=True)

    extracted_students = []

    with zipfile.ZipFile(zip_path, "r") as zf:
        for member in zf.infolist():
            if member.is_dir():
                continue

            # Moodle export format: "Apellido Nombre_ID_assignsubmission_file_filename.ext"
            filename = Path(member.filename).name
            parts = filename.split("_")
            student_raw = parts[0] if parts else "estudiante_desconocido"
            student_slug = re.sub(r"[^\w\-]", "_", student_raw.lower().strip())

            student_dir = submissions_dir / student_slug
            student_dir.mkdir(parents=True, exist_ok=True)

            target_path = student_dir / filename
            with zf.open(member) as source, open(target_path, "wb") as target:
                shutil.copyfileobj(source, target)

            # Si el alumno subió un ZIP anidado, descomprimirlo
            if target_path.suffix.lower() == ".zip":
                try:
                    with zipfile.ZipFile(target_path, "r") as sub_zf:
                        sub_zf.extractall(student_dir)
                except Exception:
                    pass

            if student_slug not in extracted_students:
                extracted_students.append(student_slug)

    return sorted(extracted_students)


def export_grades_csv(
    exercise: str,
    submissions_dir: Path,
    output_csv: Path,
    grades_map: Dict[str, float],
) -> None:
    """Exporta las calificaciones consolidadas a un archivo CSV compatible con Moodle."""
    output_csv.parent.mkdir(parents=True, exist_ok=True)

    with open(output_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Estudiante", "Actividad", "Calificacion", "Estado"])

        for student_dir in sorted(submissions_dir.iterdir()):
            if not student_dir.is_dir() or student_dir.name.startswith((".", "_")) or student_dir.name in ("guia", "guide", "templates", "informe", "baseline", "_baseline"):
                continue
            student = student_dir.name
            grade = grades_map.get(student, 0.0)
            estado = "Aprobado" if grade >= 6.0 else "Reentrega"
            writer.writerow([student, exercise, f"{grade:.1f}", estado])
