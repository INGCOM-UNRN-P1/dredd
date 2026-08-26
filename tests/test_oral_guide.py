"""Pruebas de oral-exam-companion: banderas Git y generación de guía."""

from types import SimpleNamespace

from dredd.core import oral_guide
from dredd.core.oral_guide import analizar_historial, generar_guia


def _repo_con_historial(tmp_path):
    import subprocess

    repo = tmp_path / "alumno-tp03"
    repo.mkdir()
    def git(*args):
        subprocess.run(["git", "-C", str(repo), *args],
                       capture_output=True, check=True)
    git("init", "-q", "-b", "main")
    (repo / "tp.c").write_text("#include <stdio.h>\nint main(void){return 0;}\n")
    git("add", "-A")
    git("-c", "user.name=A", "-c", "user.email=a@a", "commit", "-qm", "wip")
    (repo / "tp.c").write_text("int main(void){int x=1;return x;}\n")
    git("-c", "user.name=A", "-c", "user.email=a@a", "commit", "-qam", "fix")
    return repo


def test_banderas_detecta_mensajes_genericos(tmp_path):
    repo = _repo_con_historial(tmp_path)
    b = analizar_historial(repo)
    assert b.commits == 2
    assert b.mensajes_genericos == 2   # "wip" y "fix"


def test_repo_sin_git_devuelve_advertencia(tmp_path):
    b = analizar_historial(tmp_path)
    assert b.commits == 0
    assert any("no es un repositorio" in a for a in b.advertencias)


def test_guia_incluye_preguntas_por_bandera(tmp_path):
    import subprocess
    repo = _repo_con_historial(tmp_path)
    # un commit grande (250 líneas) dispara la bandera de análisis
    (repo / "grande.c").write_text("\n".join(f"// linea {i}" for i in range(250)))
    subprocess.run(["git", "-C", str(repo), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(repo), "-c", "user.name=A",
                    "-c", "user.email=a@a", "commit", "-qm", "tp final"],
                   check=True)

    guia = generar_guia(repo, nombre_alumno="Ana", ejercicio="TP03",
                        correr_ripley=False)
    assert "# Guía Oral — Ana — TP03" in guia
    assert "## Banderas detectadas" in guia
    assert "[Recordar]" in guia            # mensajes genéricos
    assert "[Análisis]" in guia            # commit grande


def test_preguntas_ripley_por_fugas_y_tests():
    reporte = {
        "compilation": {"success": True},
        "tests": {"total": 5, "passed": 3, "failed": 2},
        "ast_findings": [
            {"rule_id": "MEM.LEAK", "severity": "ERROR",
             "file": "tp.c", "line": 7,
             "message": "Posible fuga de memoria con malloc sin free."},
        ],
        "metrics": {"cyclomatic_complexity_max": 12},
    }
    preguntas = oral_guide._preguntas_de_reporte_ripley(reporte)
    niveles = [p["nivel"] for p in preguntas]
    assert "Análisis" in niveles          # tests fallidos
    assert "Evaluación" in niveles        # fuga + complejidad


def test_sin_senales_usa_banco_generico(tmp_path):
    vacio = tmp_path / "vacio"
    vacio.mkdir()
    guia = generar_guia(vacio, correr_ripley=False)
    assert "banco genérico" in guia
