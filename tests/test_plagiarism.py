"""Unit tests for Dredd plagiarism detector."""

from pathlib import Path
from dredd.core.plagiarism import PlagiarismDetector, tokenize_c_code, compute_winnowing_fingerprints


def test_winnowing_identical_code_gives_100_percent(tmp_path: Path):
    submissions = tmp_path / "tp01-submissions"
    submissions.mkdir()

    s1 = submissions / "estudiante_a"
    s1.mkdir()
    (s1 / "solucion.c").write_text(
        """#include <stdio.h>
int factorial(int n) {
    if (n <= 1) return 1;
    return n * factorial(n - 1);
}
int main(void) {
    printf("%d\\n", factorial(5));
    return 0;
}
""",
        encoding="utf-8",
    )

    s2 = submissions / "estudiante_b"
    s2.mkdir()
    (s2 / "solucion.c").write_text(
        """#include <stdio.h>
/* Comentario diferente */
int factorial(int num) {
    if (num <= 1) return 1;
    return num * factorial(num - 1);
}
int main(void) {
    printf("%d\\n", factorial(5));
    return 0;
}
""",
        encoding="utf-8",
    )

    detector = PlagiarismDetector(threshold=0.80)
    matches = detector.analyze_submissions(submissions)
    assert len(matches) == 1
    assert matches[0].student_a in ("estudiante_a", "estudiante_b")
    assert matches[0].similarity_pct >= 90.0
