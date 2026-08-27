"""Detector de similitud y plagio de cohorte basado en el algoritmo Winnowing."""

from dataclasses import dataclass, field
import hashlib
from pathlib import Path
import re
from typing import Dict, List, Optional, Set, Tuple

C_KEYWORDS = {
    "auto", "break", "case", "char", "const", "continue", "default", "do",
    "double", "else", "enum", "extern", "float", "for", "goto", "if",
    "int", "long", "register", "return", "short", "signed", "sizeof", "static",
    "struct", "switch", "typedef", "union", "unsigned", "void", "volatile", "while",
}


def strip_comments_and_strings(code: str) -> str:
    """Remueve comentarios de C y cadenas literales para evitar coincidencias espurias."""
    # Remover strings
    code = re.sub(r'"(\\.|[^"\\])*"', '""', code)
    # Remover char literals
    code = re.sub(r"'(\\.|[^'\\])*'", "''", code)
    # Remover comentarios multilínea
    code = re.sub(r"/\*.*?\*/", "", code, flags=re.DOTALL)
    # Remover comentarios unilínea
    code = re.sub(r"//.*", "", code)
    return code


def tokenize_c_code(code: str) -> List[Tuple[str, int]]:
    """Tokeniza código C normalizando identificadores y números para capturar similitud estructural."""
    clean_code = strip_comments_and_strings(code)
    tokens: List[Tuple[str, int]] = []

    pattern = re.compile(r"([a-zA-Z_]\w*|\d+|==|!=|<=|>=|&&|\|\||[+\-*/%<>=!&|^~?:;,.(){}\[\]])")
    for lineno, line in enumerate(clean_code.splitlines(), 1):
        for m in pattern.finditer(line):
            raw = m.group(1)
            if raw in C_KEYWORDS or not raw.isidentifier():
                tokens.append((raw, lineno))
            elif raw.isdigit():
                tokens.append(("NUM", lineno))
            else:
                tokens.append(("ID", lineno))

    return tokens


def compute_winnowing_fingerprints(tokens: List[Tuple[str, int]], k: int = 8, w: int = 4) -> Set[int]:
    """Calcula huellas digitales mediante el algoritmo Winnowing."""
    if len(tokens) < k:
        seq = "".join(t[0] for t in tokens)
        return {int(hashlib.md5(seq.encode("utf-8")).hexdigest()[:8], 16)} if seq else set()

    k_gram_hashes: List[int] = []
    for i in range(len(tokens) - k + 1):
        k_gram_str = "".join(t[0] for t in tokens[i : i + k])
        h = int(hashlib.md5(k_gram_str.encode("utf-8")).hexdigest()[:8], 16)
        k_gram_hashes.append(h)

    fingerprints: Set[int] = set()
    if len(k_gram_hashes) < w:
        return set(k_gram_hashes)

    for i in range(len(k_gram_hashes) - w + 1):
        window = k_gram_hashes[i : i + w]
        fingerprints.add(min(window))

    return fingerprints


@dataclass
class SimilarityMatch:
    student_a: str
    student_b: str
    similarity_pct: float
    shared_fingerprints: int
    total_a: int
    total_b: int


class PlagiarismDetector:
    """Analiza la cohorte de entregas descargadas en <ejercicio>-submissions/."""

    def __init__(self, k: int = 8, w: int = 4, threshold: float = 0.60,
                 plantilla: Optional[Path] = None):
        self.k = k
        self.w = w
        self.threshold = threshold
        # boiler-strip (nuevas.md): si hay plantilla de cátedra, se sanitizan
        # las entregas antes de calcular huellas.
        self._stripper = None
        if plantilla is not None:
            from dredd.core.boiler_strip import BoilerStripper
            stripper = BoilerStripper(ventanas_minimas=2)
            stripper.cargar_plantilla(plantilla)
            self._stripper = stripper

    def _codigo_sanitizado(self, student_dir: Path) -> str:
        trozos: List[str] = []
        for c_file in sorted(student_dir.glob("**/*.c")):
            code = c_file.read_text(encoding="utf-8", errors="replace")
            if self._stripper is not None:
                trozos.append(self._stripper.limpiar(code))
            else:
                trozos.append(code)
        return "\n\n".join(trozos)

    def extract_fingerprints_from_dir(self, student_dir: Path) -> Set[int]:
        fps: Set[int] = set()
        try:
            code = self._codigo_sanitizado(student_dir)
            tokens = tokenize_c_code(code)
            fps.update(compute_winnowing_fingerprints(tokens, k=self.k, w=self.w))
        except Exception:
            pass
        return fps

    def analyze_submissions(self, submissions_dir: Path, threshold: Optional[float] = None,
                            plantilla: Optional[Path] = None) -> List[SimilarityMatch]:
        if plantilla is not None and self._stripper is None:
            self.__init__(k=self.k, w=self.w, threshold=self.threshold, plantilla=plantilla)
        thresh = threshold if threshold is not None else self.threshold
        if not submissions_dir.is_dir():
            return []

        student_dirs = [
            d for d in sorted(submissions_dir.iterdir())
            if d.is_dir() and not d.name.startswith(".") and d.name not in ("guia", "guide", "templates", "informe")
        ]
        student_fps: Dict[str, Set[int]] = {}

        for s_dir in student_dirs:
            fps = self.extract_fingerprints_from_dir(s_dir)
            if fps:
                student_fps[s_dir.name] = fps

        matches: List[SimilarityMatch] = []
        students = sorted(student_fps.keys())

        for i in range(len(students)):
            for j in range(i + 1, len(students)):
                s_a, s_b = students[i], students[j]
                fps_a, fps_b = student_fps[s_a], student_fps[s_b]

                if not fps_a or not fps_b:
                    continue

                intersection = len(fps_a.intersection(fps_b))
                # Coeficiente de Jaccard / Containment máximo
                sim = (2.0 * intersection) / (len(fps_a) + len(fps_b))

                if sim >= thresh:
                    matches.append(
                        SimilarityMatch(
                            student_a=s_a,
                            student_b=s_b,
                            similarity_pct=round(sim * 100, 1),
                            shared_fingerprints=intersection,
                            total_a=len(fps_a),
                            total_b=len(fps_b),
                        )
                    )

        return sorted(matches, key=lambda m: m.similarity_pct, reverse=True)


def generate_plagiarism_html_report(
    submissions_dir: Path,
    matches: List[SimilarityMatch],
    output_html: Path,
    title: str = "Matriz de Similitud y Detección de Plagio (Winnowing)",
) -> Path:
    """Genera una matriz visual de similitud en HTML con visor diff lado a lado."""
    import difflib
    import html

    output_html = Path(output_html)
    output_html.parent.mkdir(parents=True, exist_ok=True)

    match_rows = []
    diff_sections = []

    for idx, m in enumerate(matches, 1):
        color = "#ef4444" if m.similarity_pct >= 80 else ("#f59e0b" if m.similarity_pct >= 60 else "#3b82f6")
        row = f"""
        <tr>
            <td><strong>#{idx}</strong></td>
            <td><a href="#diff-{idx}" class="pair-link">{html.escape(m.student_a)} ⟷ {html.escape(m.student_b)}</a></td>
            <td><span class="sim-pill" style="background:{color};">{m.similarity_pct:.1f}%</span></td>
            <td>{m.shared_fingerprints}</td>
            <td>{m.total_a}</td>
            <td>{m.total_b}</td>
        </tr>
        """
        match_rows.append(row)

        dir_a = submissions_dir / m.student_a
        dir_b = submissions_dir / m.student_b

        code_a = "\n\n".join(f.read_text(encoding="utf-8", errors="replace") for f in sorted(dir_a.glob("**/*.c"))) if dir_a.is_dir() else ""
        code_b = "\n\n".join(f.read_text(encoding="utf-8", errors="replace") for f in sorted(dir_b.glob("**/*.c"))) if dir_b.is_dir() else ""

        diff_html = difflib.HtmlDiff(wrapcolumn=60).make_table(
            code_a.splitlines(),
            code_b.splitlines(),
            fromdesc=f"Estudiante A: {m.student_a}",
            todesc=f"Estudiante B: {m.student_b}",
            context=True,
            numlines=3,
        )

        section = f"""
        <div class="diff-card" id="diff-{idx}">
            <div class="diff-header">
                <h3>Coincidencia #{idx}: {html.escape(m.student_a)} vs {html.escape(m.student_b)}</h3>
                <span class="sim-pill" style="background:{color};">{m.similarity_pct:.1f}% Similitud</span>
            </div>
            <div class="diff-body">
                {diff_html}
            </div>
        </div>
        """
        diff_sections.append(section)

    table_rows_html = "\n".join(match_rows) if match_rows else "<tr><td colspan='6'>No se detectaron pares con similitud superior al umbral.</td></tr>"
    diffs_html_block = "\n".join(diff_sections)

    html_page = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>{html.escape(title)}</title>
    <style>
        body {{ background: #0f172a; color: #f8fafc; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; padding: 2rem; }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        h1 {{ font-size: 1.6rem; margin-bottom: 0.5rem; color: #38bdf8; }}
        p.subtitle {{ color: #94a3b8; margin-bottom: 1.5rem; }}
        table.matrix-table {{ width: 100%; border-collapse: collapse; background: #1e293b; border-radius: 8px; overflow: hidden; margin-bottom: 2rem; }}
        th, td {{ padding: 0.8rem 1rem; text-align: left; border-bottom: 1px solid #334155; }}
        th {{ background: #0b1120; color: #cbd5e1; font-weight: 700; }}
        .sim-pill {{ padding: 0.25rem 0.6rem; border-radius: 9999px; font-weight: 700; color: #fff; font-size: 0.85rem; }}
        .pair-link {{ color: #38bdf8; text-decoration: none; font-weight: 600; }}
        .pair-link:hover {{ text-decoration: underline; }}
        .diff-card {{ background: #1e293b; border: 1px solid #334155; border-radius: 8px; margin-bottom: 1.5rem; overflow: hidden; }}
        .diff-header {{ background: #0b1120; padding: 0.9rem 1.2rem; display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #334155; }}
        .diff-body {{ padding: 1rem; overflow-x: auto; }}
        table.diff {{ width: 100%; font-family: monospace; font-size: 0.85rem; color: #e2e8f0; }}
        .diff_header {{ background: #334155; color: #94a3b8; padding: 0.2rem 0.5rem; }}
        .diff_next {{ background: #1e293b; }}
        .diff_add {{ background: #064e3b; color: #6ee7b7; }}
        .diff_chg {{ background: #451a03; color: #fcd34d; }}
        .diff_sub {{ background: #450a0a; color: #fca5a5; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 {html.escape(title)}</h1>
        <p class="subtitle">Directorio de entregas: <code>{html.escape(str(submissions_dir))}</code> · Total pares sospechosos: {len(matches)}</p>

        <h2>Matriz de Coincidencias</h2>
        <table class="matrix-table">
            <thead>
                <tr>
                    <th>#</th>
                    <th>Pares de Estudiantes</th>
                    <th>Similitud</th>
                    <th>Huellas Compartidas</th>
                    <th>Huellas A</th>
                    <th>Huellas B</th>
                </tr>
            </thead>
            <tbody>
                {table_rows_html}
            </tbody>
        </table>

        <h2>Comparación Lado a Lado (Diff Resaltado)</h2>
        {diffs_html_block}
    </div>
</body>
</html>"""

    output_html.write_text(html_page, encoding="utf-8")
    return output_html

