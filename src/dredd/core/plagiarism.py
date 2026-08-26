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

        student_dirs = [d for d in sorted(submissions_dir.iterdir()) if d.is_dir() and not d.name.startswith(".")]
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
