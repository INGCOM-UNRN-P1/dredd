"""Moodle grades exporter, feedback packager and cohort dashboard generator."""

import csv
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional
import zipfile

from dredd.core.db import DatabaseManager


def _nota(valor: Optional[float], formato: str, vacio: str = "—") -> str:
    return vacio if valor is None else format(valor, formato)


def _promedio(valores: Iterable[Optional[float]]) -> Optional[float]:
    conocidos = [v for v in valores if v is not None]
    return sum(conocidos) / len(conocidos) if conocidos else None


@dataclass
class CohortMetrics:
    total_students: int
    compiled_count: int
    compilation_rate_pct: float
    avg_grade: float
    avg_style: float
    top_style_errors: List[tuple[str, int]]
    student_summaries: List[Dict[str, Any]]


class MoodleExporter:
    """Exporta calificaciones y retroalimentación compatibles con Moodle y genera el dashboard docente."""

    def __init__(self, workspace_dir: str | Path = ".") -> None:
        self.workspace_dir = Path(workspace_dir)

    def _activity_dir(self, activity_slug: str) -> Path:
        """El directorio de entregas de la actividad, el mismo que usa `eval` (p. ej. entregas/TP0).

        Antes las salidas por omisión iban a `<workspace>/<actividad>/` y creaban una carpeta
        espuria en la raíz (F-03).
        """
        from dredd.core.git_ops import resolve_submissions_dir

        return resolve_submissions_dir(self.workspace_dir, activity_slug)[1]

    def _get_all_activity_data(self, activity_slug: str) -> List[Dict[str, Any]]:
        from dredd.core import auditoria

        activity_dir = self._activity_dir(activity_slug)
        if not activity_dir.exists():
            raise FileNotFoundError(f"Directorio de actividad no encontrado: {activity_dir}")

        students_data: List[Dict[str, Any]] = []

        for s_dir in sorted(activity_dir.iterdir()):
            if not s_dir.is_dir() or s_dir.name.startswith((".", "_")) or s_dir.name in ("guia", "guide", "templates", "informe", "baseline", "_baseline"):
                continue

            db_path = s_dir / ".metadata.db"
            student_name = s_dir.name
            student_id = "0"
            submission_id = "0"
            version_num = 1
            revision = "r1"
            folder_path = str(s_dir)
            # Sin .metadata.db (repos de GitHub) el estado sale del auditoria.json de la última
            # revisión; lo que no se sabe queda en None y no se exporta como un 0.
            compilation_status = "SIN EVALUAR"
            preliminary_grade: Optional[float] = None
            grade_style: Optional[float] = None
            grade_tests: Optional[float] = None

            if db_path.exists():
                db = DatabaseManager(db_path)
                with db._get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT * FROM students WHERE slug = ?", (s_dir.name,))
                    student_row = cursor.fetchone()
                    if student_row:
                        student_name = student_row["full_name"]
                        student_id = student_row["student_id"]
                        submission_id = student_row["submission_id"]

                    latest_rev = db.get_latest_revision(s_dir.name)
                    if latest_rev:
                        version_num = latest_rev["version_num"]
                        revision = f"r{version_num}"
                        folder_path = latest_rev["folder_path"]
                        cursor.execute(
                            "SELECT * FROM evaluations WHERE revision_id = ?", (latest_rev["id"],)
                        )
                        eval_row = cursor.fetchone()
                        if eval_row:
                            compilation_status = eval_row["compilation_status"]
                            preliminary_grade = eval_row["preliminary_grade"]
                            grade_style = eval_row["grade_style"]
                            grade_tests = eval_row["grade_tests"]
            else:
                ultima = auditoria.ultima_revision(s_dir)
                registro = auditoria.leer(ultima) if ultima else None
                if registro:
                    revision = str(registro.get("revision") or revision)
                    folder_path = str(ultima)
                    resultado = registro.get("resultado")
                    if registro.get("estado") == "completa" and resultado:
                        compilation_status = "OK" if resultado.get("compilacion") else "FAIL"
                        tests = resultado.get("tests") or {}
                        if int(tests.get("total") or 0) > 0:
                            grade_tests = 10.0 * int(tests.get("aprobados") or 0) / int(tests["total"])
                    else:
                        compilation_status = "INCOMPLETA"
                else:
                    # Evaluada antes de que existiera el cursor (Ola 8): se sabe la revisión, no el resultado.
                    from dredd.core.eval_clean import es_directorio_rni

                    intermedios = [d for d in s_dir.iterdir() if es_directorio_rni(d)]
                    if intermedios:
                        ultimo = max(intermedios, key=lambda d: d.stat().st_mtime).name
                        revision = ultimo[2:] if ultimo.lower().startswith("i_") else ultimo[:-1]
                        compilation_status = "SIN REGISTRO"

            clean_slug = Path(activity_slug).name or activity_slug.strip("/\\")
            rep_candidate = s_dir / f"{s_dir.name}_{revision}.md"
            if not rep_candidate.exists():
                rep_candidate = s_dir / f"{s_dir.name}_{clean_slug}.md"
            if not rep_candidate.exists():
                if (s_dir / f"{s_dir.name}.md").exists():
                    rep_candidate = s_dir / f"{s_dir.name}.md"
                else:
                    mds = [f for f in s_dir.glob("*.md") if f.is_file()]
                    if mds:
                        mds.sort(key=lambda p: (p.stat().st_mtime, p.name), reverse=True)
                        rep_candidate = mds[0]

            s_dict = {
                "slug": s_dir.name,
                "student_name": student_name,
                "student_id": student_id,
                "submission_id": submission_id,
                "version_num": version_num,
                "revision": revision,
                "folder_path": folder_path,
                "compilation_status": compilation_status,
                "preliminary_grade": preliminary_grade,
                "grade_style": grade_style,
                "grade_tests": grade_tests,
                "report_file": rep_candidate,
            }
            students_data.append(s_dict)

        return students_data

    def export_grades_csv(
        self,
        activity_slug: str,
        output_file: Optional[Path | str] = None,
    ) -> Path:
        """Exporta CSV estructurado para importar al Libro de Calificaciones de Moodle."""
        csv_path = Path(output_file) if output_file else self._activity_dir(activity_slug) / "moodle_grades.csv"
        data = self._get_all_activity_data(activity_slug)  # antes del mkdir: sin entregas no crea nada
        csv_path.parent.mkdir(parents=True, exist_ok=True)

        fieldnames = [
            "Identificador",
            "Nombre completo",
            "Número de ID",
            "Calificación",
            "Última modificación (calificación)",
            "Comentarios de retroalimentación",
        ]

        with open(csv_path, mode="w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            for item in data:
                # Una calificación vacía no pisa la de Moodle al importar; un 0 sí.
                grade_str = _nota(item["preliminary_grade"], ".2f", "")
                feedback = (
                    f"Revisión {item['revision']} | "
                    f"Compilación: {item['compilation_status']} | "
                    f"Estilo: {_nota(item['grade_style'], '.1f')}/10 | "
                    f"Tests: {_nota(item['grade_tests'], '.1f')}/10"
                )
                writer.writerow(
                    {
                        "Identificador": f"Participante {item['submission_id']}",
                        "Nombre completo": item["student_name"],
                        "Número de ID": item["student_id"],
                        "Calificación": grade_str,
                        "Última modificación (calificación)": datetime.now().strftime("%d/%m/%Y %H:%M"),
                        "Comentarios de retroalimentación": feedback,
                    }
                )

        return csv_path

    def export_feedback_zip(
        self,
        activity_slug: str,
        output_file: Optional[Path | str] = None,
    ) -> Path:
        """Empaqueta los informes Markdown en un ZIP listo para retroalimentación masiva de Moodle."""
        zip_path = Path(output_file) if output_file else self._activity_dir(activity_slug) / "retroalimentacion_moodle.zip"
        data = self._get_all_activity_data(activity_slug)  # antes del mkdir: sin entregas no crea nada
        zip_path.parent.mkdir(parents=True, exist_ok=True)

        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for item in data:
                report_file = item["report_file"]
                if report_file.exists():
                    moodle_folder_name = f"{item['student_name']}_{item['submission_id']}_assignsubmission_file"
                    arcname = f"{moodle_folder_name}/{report_file.name}"
                    zf.write(report_file, arcname=arcname)

        return zip_path

    def generate_dashboard(
        self,
        activity_slug: str,
        output_file: Optional[Path | str] = None,
    ) -> Path:
        """Genera un reporte consolidado dashboard.md para el docente con métricas de la cohorte."""
        dash_path = Path(output_file) if output_file else self._activity_dir(activity_slug) / "dashboard.md"
        data = self._get_all_activity_data(activity_slug)  # antes del mkdir: sin entregas no crea nada
        dash_path.parent.mkdir(parents=True, exist_ok=True)
        total = len(data)
        if total == 0:
            dash_path.write_text(f"# Dashboard de Cohorte - {activity_slug}\n\nSin entregas evaluadas.\n", encoding="utf-8")
            return dash_path

        compiled_count = sum(1 for d in data if d["compilation_status"] == "OK")
        compilation_rate = (compiled_count / total) * 100.0
        avg_grade = _promedio(d["preliminary_grade"] for d in data)
        avg_style = _promedio(d["grade_style"] for d in data)

        lines: List[str] = [
            f"# Dashboard de Cohorte - Actividad: {activity_slug}",
            f"**Fecha de generación:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  ",
            f"**Total de entregas evaluadas:** {total}\n",
            "## Métricas Generales\n",
            f"- **Tasa de Compilación:** {compilation_rate:.1f}% ({compiled_count}/{total})",
            f"- **Promedio de Nota Preliminar:** {_nota(avg_grade, '.2f')} / 10.0",
            f"- **Cumplimiento de Estilo Promedio:** {_nota(avg_style, '.2f')} / 10.0\n",
            "## Resumen Consolidado por Estudiante\n",
            "| Estudiante | ID Entrega | Revisión | Compilación | Estilo | Tests I/O | Nota Preliminar |",
            "| ---------- | ---------- | -------- | ----------- | ------ | --------- | --------------- |",
        ]

        for item in data:
            estado = item["compilation_status"]
            comp_badge = "✓ OK" if estado == "OK" else ("✗ FAIL" if estado == "FAIL" else estado.lower())
            lines.append(
                f"| `{item['student_name']}` | {item['submission_id']} | {item['revision']} | {comp_badge} | {_nota(item['grade_style'], '.1f')} | {_nota(item['grade_tests'], '.1f')} | **{_nota(item['preliminary_grade'], '.2f')}** |"
            )

        lines.append("\n---\n*Generado automáticamente por Dredd.*")
        dash_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return dash_path
