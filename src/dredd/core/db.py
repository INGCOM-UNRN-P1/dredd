"""Capa de persistencia SQLite para metadatos de estudiantes, versiones de entrega y evaluaciones."""

from dataclasses import dataclass
from pathlib import Path
import sqlite3
from typing import Any, Dict, List, Optional


@dataclass
class StudentRecord:
    student_id: str
    full_name: str
    slug: str
    submission_id: str


@dataclass
class RevisionRecord:
    id: Optional[int]
    student_slug: str
    version_num: int
    created_at: str
    sources_hash: str
    folder_path: str


class DatabaseManager:
    """Administra la base de datos SQLite (.metadata.db) de entregas y evaluaciones."""

    def __init__(self, db_path: Path | str) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS students (
                    slug TEXT PRIMARY KEY,
                    student_id TEXT,
                    full_name TEXT,
                    submission_id TEXT
                );
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS revisions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    student_slug TEXT,
                    version_num INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    sources_hash TEXT,
                    folder_path TEXT,
                    FOREIGN KEY(student_slug) REFERENCES students(slug)
                );
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS source_files (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    revision_id INTEGER,
                    filename TEXT,
                    file_hash TEXT,
                    size_bytes INTEGER,
                    FOREIGN KEY(revision_id) REFERENCES revisions(id)
                );
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS ignored_files (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    revision_id INTEGER,
                    filename TEXT,
                    reason TEXT,
                    FOREIGN KEY(revision_id) REFERENCES revisions(id)
                );
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS evaluations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    revision_id INTEGER UNIQUE,
                    evaluated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    compilation_status TEXT,
                    preliminary_grade REAL,
                    grade_compilation REAL,
                    grade_style REAL,
                    grade_linter REAL,
                    grade_tests REAL,
                    unified_diff TEXT,
                    compilation_logs TEXT,
                    FOREIGN KEY(revision_id) REFERENCES revisions(id)
                );
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS test_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    evaluation_id INTEGER,
                    exercise TEXT,
                    test_case TEXT,
                    cli_args TEXT,
                    result TEXT,
                    exec_time_ms REAL,
                    FOREIGN KEY(evaluation_id) REFERENCES evaluations(id)
                );
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS submission_states (
                    actividad TEXT NOT NULL,
                    alumno TEXT NOT NULL,
                    estado TEXT NOT NULL DEFAULT 'ingresada',
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (actividad, alumno)
                );
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS audit_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    actividad TEXT NOT NULL,
                    alumno TEXT NOT NULL,
                    estado_anterior TEXT,
                    estado_nuevo TEXT NOT NULL,
                    actor TEXT DEFAULT '',
                    nota TEXT DEFAULT '',
                    forzado INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            conn.commit()

    def upsert_student(self, student: StudentRecord) -> None:
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO students (slug, student_id, full_name, submission_id)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(slug) DO UPDATE SET
                    student_id=excluded.student_id,
                    full_name=excluded.full_name,
                    submission_id=excluded.submission_id
            """,
                (student.slug, student.student_id, student.full_name, student.submission_id),
            )
            conn.commit()

    def get_latest_revision(self, student_slug: str) -> Optional[sqlite3.Row]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM revisions
                WHERE student_slug = ?
                ORDER BY version_num DESC
                LIMIT 1
            """,
                (student_slug,),
            )
            return cursor.fetchone()

    def get_all_revisions(self, student_slug: str) -> List[sqlite3.Row]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM revisions
                WHERE student_slug = ?
                ORDER BY version_num ASC
            """,
                (student_slug,),
            )
            return cursor.fetchall()

    def add_revision(
        self,
        student_slug: str,
        version_num: int,
        sources_hash: str,
        folder_path: str,
        sources: List[Dict[str, Any]],
        ignored: List[Dict[str, str]],
    ) -> int:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO revisions (student_slug, version_num, sources_hash, folder_path)
                VALUES (?, ?, ?, ?)
            """,
                (student_slug, version_num, sources_hash, folder_path),
            )
            rev_id = cursor.lastrowid
            if rev_id is None:
                raise RuntimeError("No se pudo obtener el ID de la revisión insertada.")

            for src in sources:
                cursor.execute(
                    """
                    INSERT INTO source_files (revision_id, filename, file_hash, size_bytes)
                    VALUES (?, ?, ?, ?)
                """,
                    (rev_id, src["filename"], src["file_hash"], src["size_bytes"]),
                )

            for ign in ignored:
                cursor.execute(
                    """
                    INSERT INTO ignored_files (revision_id, filename, reason)
                    VALUES (?, ?, ?)
                """,
                    (rev_id, ign["filename"], ign.get("reason", "Archivo no permitido")),
                )

            conn.commit()
            return rev_id

    def save_evaluation(
        self,
        revision_id: int,
        compilation_status: str,
        preliminary_grade: float,
        grade_compilation: float,
        grade_style: float,
        grade_linter: float,
        grade_tests: float,
        unified_diff: str = "",
        compilation_logs: str = "",
        test_results: Optional[List[Dict[str, Any]]] = None,
    ) -> int:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO evaluations (
                    revision_id, compilation_status, preliminary_grade,
                    grade_compilation, grade_style, grade_linter, grade_tests,
                    unified_diff, compilation_logs
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(revision_id) DO UPDATE SET
                    evaluated_at=CURRENT_TIMESTAMP,
                    compilation_status=excluded.compilation_status,
                    preliminary_grade=excluded.preliminary_grade,
                    grade_compilation=excluded.grade_compilation,
                    grade_style=excluded.grade_style,
                    grade_linter=excluded.grade_linter,
                    grade_tests=excluded.grade_tests,
                    unified_diff=excluded.unified_diff,
                    compilation_logs=excluded.compilation_logs
            """,
                (
                    revision_id,
                    compilation_status,
                    preliminary_grade,
                    grade_compilation,
                    grade_style,
                    grade_linter,
                    grade_tests,
                    unified_diff,
                    compilation_logs,
                ),
            )
            eval_id = cursor.lastrowid
            if eval_id is None:
                cursor.execute(
                    "SELECT id FROM evaluations WHERE revision_id = ?", (revision_id,)
                )
                row = cursor.fetchone()
                eval_id = row["id"]

            cursor.execute("DELETE FROM test_results WHERE evaluation_id = ?", (eval_id,))
            if test_results:
                for tr in test_results:
                    cursor.execute(
                        """
                        INSERT INTO test_results (evaluation_id, exercise, test_case, cli_args, result, exec_time_ms)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """,
                        (
                            eval_id,
                            tr.get("exercise", ""),
                            tr.get("test_case", ""),
                            tr.get("cli_args", ""),
                            tr.get("result", ""),
                            tr.get("exec_time_ms", 0.0),
                        ),
                    )

            conn.commit()
            return eval_id

    def get_student_evaluation(self, revision_id: int) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM evaluations WHERE revision_id = ?", (revision_id,))
            eval_row = cursor.fetchone()
            if not eval_row:
                return None
            res = dict(eval_row)
            cursor.execute(
                "SELECT * FROM test_results WHERE evaluation_id = ?", (eval_row["id"],)
            )
            res["test_results"] = [dict(r) for r in cursor.fetchall()]
            return res

