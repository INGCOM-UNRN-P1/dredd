"""Similitud estructural en la cohorte: `dredd cluster-errors --similitud` (Ola 8)."""

import json
import sys
from pathlib import Path

import pytest
from typer.testing import CliRunner

from dredd.cli import app
from dredd.core.cohorte import escribir
from dredd.core.similitud import agrupar, fuentes_de_revision, informe_markdown

runner = CliRunner()

ORIGINAL = """#include <stdio.h>

int sumar_pares(const int *valores, int cantidad)
{
    int total = 0;
    for (int i = 0; i < cantidad; i++) {
        if (valores[i] % 2 == 0) {
            total += valores[i];
        }
    }
    return total;
}

int main(void)
{
    int datos[] = {1, 2, 3, 4};
    printf("%d\\n", sumar_pares(datos, 4));
    return 0;
}
"""

# Lo mismo con otros nombres, comentarios, otro formato, un prototipo y las funciones en otro orden.
MAQUILLADO = """#include <stdio.h>
int acumular(const int *arreglo, int largo);

/* programa principal */
int main(void) {
    int numeros[] = {1, 2, 3, 4};
    printf("%d\\n", acumular(numeros, 4));  // muestra la suma
    return 0;
}

int acumular(const int *arreglo, int largo) {
    int suma = 0;
    for (int k = 0; k < largo; k++) { if (arreglo[k] % 2 == 0) { suma += arreglo[k]; } }
    return suma;
}
"""

DISTINTO = """#include <stdio.h>
#include <stdlib.h>

typedef struct nodo { int valor; struct nodo *siguiente; } nodo_t;

nodo_t *apilar(nodo_t *tope, int valor)
{
    nodo_t *nuevo = malloc(sizeof *nuevo);
    if (nuevo == NULL) {
        return tope;
    }
    nuevo->valor = valor;
    nuevo->siguiente = tope;
    return nuevo;
}

int main(void)
{
    nodo_t *pila = NULL;
    while (scanf("%d", &(int){0}) == 1) {
        pila = apilar(pila, 1);
    }
    return pila == NULL;
}
"""


@pytest.fixture
def curso(tmp_path: Path) -> Path:
    for alumno, codigo in (("ana", ORIGINAL), ("beto", MAQUILLADO), ("caro", DISTINTO)):
        (tmp_path / alumno / "r1").mkdir(parents=True)
        (tmp_path / alumno / "r1" / "main.c").write_text(codigo)
        escribir(tmp_path / alumno / "r1i", {})
    (tmp_path / "dani" / "r1i").mkdir(parents=True)
    escribir(tmp_path / "dani" / "r1i", {})
    return tmp_path


def _entregas(curso: Path):
    return {a: fuentes_de_revision(curso / a / "r1i") for a in ("ana", "beto", "caro", "dani")}


@pytest.fixture(params=["weyl", "dredd"])
def con_motor(request, monkeypatch):
    if request.param == "weyl":
        raiz_weyl = Path(__file__).resolve().parents[2] / "weyl" / "src"
        if raiz_weyl.is_dir():
            monkeypatch.syspath_prepend(str(raiz_weyl))
        pytest.importorskip("weyl.core.alpha_equiv")
    else:
        monkeypatch.setitem(sys.modules, "weyl.core.alpha_equiv", None)
    return request.param


def test_agrupa_el_mismo_programa_maquillado(curso, con_motor):
    datos = agrupar(_entregas(curso), umbral=90)
    assert datos["motor"] == con_motor
    assert [g["alumnos"] for g in datos["grupos"]] == [["ana", "beto"]]
    grupo = datos["grupos"][0]
    assert grupo["matriz"]["ana"]["beto"] == grupo["matriz"]["beto"]["ana"] == 100.0
    assert datos["sin_codigo"] == ["dani"] and datos["estudiantes"] == 4
    assert all("caro" not in (p["a"], p["b"]) for p in datos["pares"])


def test_el_informe_no_expone_codigo(curso):
    texto = informe_markdown(agrupar(_entregas(curso), umbral=90))
    assert "| **ana** | — |" in texto and "Grupo 1: 2 entregas" in texto
    for fragmento in ("acumular", "sumar_pares", "printf", "valores", "apilar"):
        assert fragmento not in texto


def test_la_plantilla_de_la_catedra_no_cuenta(tmp_path):
    comun = "\n".join(f"int auxiliar_{i}(int x) {{ return x * {i} + {i}; }}" for i in range(30))
    for alumno, propio in (("ana", "int f(int a) { return a + 1; }"),
                           ("beto", "int g(char *s) { int n = 0; while (s[n]) { n++; } return n; }")):
        (tmp_path / alumno / "r1").mkdir(parents=True)
        (tmp_path / alumno / "r1" / "main.c").write_text(comun + "\n" + propio + "\n")
    plantilla = tmp_path / "plantilla.c"
    plantilla.write_text(comun + "\n")
    entregas = {a: fuentes_de_revision(tmp_path / a / "r1i") for a in ("ana", "beto")}
    assert agrupar(entregas, umbral=80)["grupos"]
    assert not agrupar(entregas, umbral=80, plantilla=plantilla)["grupos"]


def test_fuentes_de_cada_modo(tmp_path):
    (tmp_path / "ana" / "r2").mkdir(parents=True)
    (tmp_path / "ana" / "r2" / "main.c").write_text("int main(void) { return 0; }")
    (tmp_path / "ana" / "r2" / "r2i").mkdir()
    (tmp_path / "ana" / "r2" / "r2i" / "copia.c").write_text("")
    assert fuentes_de_revision(tmp_path / "ana" / "r2i") == [tmp_path / "ana" / "r2" / "main.c"]
    (tmp_path / "beto" / "repo" / "src").mkdir(parents=True)
    (tmp_path / "beto" / "repo" / "src" / "lista.c").write_text("")
    (tmp_path / "beto" / "repo" / ".git").mkdir()
    (tmp_path / "beto" / "repo" / ".git" / "x.c").write_text("")
    assert fuentes_de_revision(tmp_path / "beto" / "i_abc1234") == [tmp_path / "beto" / "repo" / "src" / "lista.c"]


def test_cli(curso, tmp_path):
    informe = tmp_path / "salida" / "similitud.md"
    res = runner.invoke(app, ["cluster-errors", str(curso), "--similitud", "--json", "--informe", str(informe)])
    assert res.exit_code == 0, res.output
    datos = json.loads(res.stdout)
    assert [g["alumnos"] for g in datos["similitud"]["grupos"]] == [["ana", "beto"]]
    assert informe.is_file()
    res = runner.invoke(app, ["cluster-errors", str(curso), "--similitud"])
    assert res.exit_code == 0, res.output
    assert "ana, beto" in res.output
    (curso / "beto" / "r1" / "main.c").write_text(DISTINTO.replace("apilar", "push"))
    res = runner.invoke(app, ["cluster-errors", str(curso), "--similitud", "--umbral", "99"])
    assert res.exit_code == 0, res.output
    assert "ana, beto" not in res.output and "caro, beto" not in res.output and "beto, caro" in res.output
