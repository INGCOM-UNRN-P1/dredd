"""`dredd moodle paquete`: notas de deckard a la hoja de calificaciones de la tarea (Ola 46)."""

import csv
import zipfile
from pathlib import Path

import pytest
from typer.testing import CliRunner

from dredd.cli import app
from dredd.core.moodle_paquete import PaqueteError, armar_paquete, detectar_columnas

runner = CliRunner()
ES = ["Identificador", "Nombre completo", "Dirección de correo", "Estado", "Calificación", "Calificación máxima",
      "La calificación puede ser cambiada", "Última modificación (entrega)", "Última modificación (calificación)",
      "Comentarios de retroalimentación"]
EN = ["Identifier", "Full name", "Email address", "Status", "Grade", "Maximum Grade", "Grade can be changed",
      "Last modified (submission)", "Last modified (grade)", "Feedback comments"]


def _planilla(ruta: Path, encabezados=ES, maximo="10,00", prefijo="Participante"):
    filas = [(f"{prefijo} 101", "Juan Pérez", "juan@unrn.edu.ar"), (f"{prefijo} 102", "Ana Gómez", "ana@unrn.edu.ar"),
             (f"{prefijo} 103", "Luz Díaz", "luz@unrn.edu.ar")]
    with open(ruta, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(encabezados)
        for ident, nombre, correo in filas:
            w.writerow([ident, nombre, correo, "Enviado", "", maximo, "Sí", "2026-11-01 10:00", "-", "comentario anterior"])
    return ruta


def _notas(base: Path, filas):
    base.mkdir(exist_ok=True)
    (base / "devoluciones").mkdir(exist_ok=True)
    ruta = base / "calificaciones.csv"
    with open(ruta, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["Usuario", "Calificación", "Provisoria", "Revisión", "Comentarios de retroalimentación"])
        for alumno, nota, provisoria in filas:
            w.writerow([alumno, nota, provisoria, "abc", f"Revisión abc | {alumno} <ok>"])
            (base / "devoluciones" / f"{alumno}.md").write_text(f"# Devolución de {alumno}\n\nBien.\n", encoding="utf-8")
    return ruta


def _leer(ruta: Path):
    with open(ruta, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def test_completa_la_hoja_sin_tocar_el_resto(tmp_path):
    planilla = _planilla(tmp_path / "hoja.csv")
    res = armar_paquete(planilla, _notas(tmp_path / "n", [("juan-perez_101", "7.50", "no")]), tmp_path / "s")
    filas = _leer(res.planilla)
    assert list(filas[0]) == ES, "los encabezados de Moodle no cambian"
    assert filas[0]["Calificación"] == "7.50"
    assert filas[0]["Comentarios de retroalimentación"] == "Revisión abc | juan-perez_101 &lt;ok&gt;"
    assert filas[0]["Última modificación (calificación)"] == "-" and filas[0]["Identificador"] == "Participante 101"
    assert filas[1]["Calificación"] == "" and filas[1]["Comentarios de retroalimentación"] == "comentario anterior"
    assert res.filas_sin_nota == 2


def test_funciona_con_un_moodle_en_ingles(tmp_path):
    planilla = _planilla(tmp_path / "hoja.csv", EN, "10.00", "Participant")
    res = armar_paquete(planilla, _notas(tmp_path / "n", [("Ana Gómez", "9", "no")]), tmp_path / "s")
    assert _leer(res.planilla)[1]["Grade"] == "9.00"


def test_vincula_por_mapa_con_identificador_correo_o_nombre(tmp_path):
    mapa = tmp_path / "mapa.csv"
    mapa.write_text("alumno,moodle\nTP0-juan,Participante 101\nTP0-ana,ana@unrn.edu.ar\nTP0-luz,Luz Díaz\n", encoding="utf-8")
    notas = _notas(tmp_path / "n", [("TP0-juan", "1", "no"), ("TP0-ana", "2", "no"), ("TP0-luz", "3", "no")])
    res = armar_paquete(_planilla(tmp_path / "hoja.csv"), notas, tmp_path / "s", mapa=mapa)
    assert [f["Calificación"] for f in _leer(res.planilla)] == ["1.00", "2.00", "3.00"]


def test_quien_no_se_vincula_queda_afuera_y_no_se_adivina(tmp_path):
    res = armar_paquete(_planilla(tmp_path / "hoja.csv"), _notas(tmp_path / "n", [("TP0-juanp", "5", "no"), ("Juan", "5", "no")]),
                        tmp_path / "s")
    assert res.sin_vincular == ["TP0-juanp", "Juan"] and res.importadas == []


def test_un_nombre_repetido_no_sirve_para_vincular(tmp_path):
    planilla = tmp_path / "hoja.csv"
    with open(planilla, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(ES)
        for n in (1, 2):
            w.writerow([f"Participante {n}", "Ana Gómez", f"a{n}@x.ar", "", "", "10", "", "", "", ""])
    res = armar_paquete(planilla, _notas(tmp_path / "n", [("Ana Gómez", "5", "no")]), tmp_path / "s")
    assert res.sin_vincular == ["Ana Gómez"]


def test_dos_estudiantes_en_la_misma_fila_es_un_error(tmp_path):
    mapa = tmp_path / "mapa.csv"
    mapa.write_text("a,Participante 101\nb,Participante 101\n", encoding="utf-8")
    with pytest.raises(PaqueteError, match="misma fila"):
        armar_paquete(_planilla(tmp_path / "hoja.csv"), _notas(tmp_path / "n", [("a", "1", "no"), ("b", "2", "no")]),
                      tmp_path / "s", mapa=mapa)


def test_una_provisoria_deja_la_fila_intacta_comentario_incluido(tmp_path):
    notas = _notas(tmp_path / "n", [("Juan Pérez", "8", "sí")])
    res = armar_paquete(_planilla(tmp_path / "hoja.csv"), notas, tmp_path / "s")
    fila = _leer(res.planilla)[0]
    assert res.provisorias == ["Juan Pérez"] and res.zip is None
    assert fila["Calificación"] == "" and fila["Comentarios de retroalimentación"] == "comentario anterior"
    res = armar_paquete(_planilla(tmp_path / "hoja.csv"), notas, tmp_path / "s2", incluir_provisorias=True)
    assert _leer(res.planilla)[0]["Calificación"] == "8.00"


@pytest.mark.parametrize("maximo, esperada", [("100,00", "75.00"), ("10.00", "7.50"), ("20", "15.00")])
def test_reescala_al_maximo_de_la_tarea(tmp_path, maximo, esperada):
    res = armar_paquete(_planilla(tmp_path / "hoja.csv", maximo=maximo), _notas(tmp_path / "n", [("Juan Pérez", "7.5", "no")]),
                        tmp_path / "s")
    assert _leer(res.planilla)[0]["Calificación"] == esperada


def test_sin_maximo_conocido_no_escribe_una_nota_mal(tmp_path):
    planilla = _planilla(tmp_path / "hoja.csv", maximo="")
    notas = _notas(tmp_path / "n", [("Juan Pérez", "7.5", "no")])
    with pytest.raises(PaqueteError, match="--maximo"):
        armar_paquete(planilla, notas, tmp_path / "s")
    assert _leer(armar_paquete(planilla, notas, tmp_path / "s", maximo=100).planilla)[0]["Calificación"] == "75.00"


def test_zip_con_la_forma_que_lee_moodle(tmp_path):
    notas = _notas(tmp_path / "n", [("Juan Pérez", "7", "no"), ("Ana Gómez", "8", "no")])
    res = armar_paquete(_planilla(tmp_path / "hoja.csv"), notas, tmp_path / "s")
    with zipfile.ZipFile(res.zip) as zf:
        nombres = sorted(zf.namelist())
        assert nombres == ["Ana Gómez_102_assignfeedback_file/devolucion.html",
                           "Juan Pérez_101_assignfeedback_file/devolucion.html"]
        contenido = zf.read(nombres[0]).decode("utf-8")
    assert "Devolución de Ana Gómez" in contenido
    # El código de importación de Moodle: explode('_', parte, 5), con el número en el segundo campo.
    assert nombres[0].split("/")[0].split("_", 4)[1:] == ["102", "assignfeedback", "file"]


def test_un_guion_bajo_en_el_nombre_no_corre_el_numero(tmp_path):
    planilla = tmp_path / "hoja.csv"
    with open(planilla, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(ES)
        w.writerow(["Participante 7", "Ana_María", "a@x.ar", "", "", "10", "", "", "", ""])
    res = armar_paquete(planilla, _notas(tmp_path / "n", [("x_7", "5", "no")]), tmp_path / "s")
    with zipfile.ZipFile(res.zip) as zf:
        assert zf.namelist()[0].split("_")[1] == "7"


def test_respeta_el_separador_de_la_planilla(tmp_path):
    planilla = tmp_path / "hoja.csv"
    planilla.write_text(";".join(ES) + "\nParticipante 1;Ana Gómez;a@x.ar;;;10;;;;\n", encoding="utf-8")
    res = armar_paquete(planilla, _notas(tmp_path / "n", [("Ana Gómez", "5", "no")]), tmp_path / "s")
    assert res.planilla.read_text(encoding="utf-8").splitlines()[1].startswith("Participante 1;Ana Gómez;")


def test_columnas_ambiguas_o_ausentes_se_explican():
    with pytest.raises(PaqueteError, match="Comentarios de retroalimentación"):
        detectar_columnas([c for c in ES if "Comentarios" not in c])
    with pytest.raises(PaqueteError, match="calificación"):
        detectar_columnas(["Identificador", "Nombre completo", "Comentarios de retroalimentación"])
    assert detectar_columnas(["Identificador", "Nombre completo", "Puntos", "Comentarios"], columna_nota="Puntos").nota == "Puntos"


def test_notas_que_no_son_de_deckard(tmp_path):
    otra = tmp_path / "otra.csv"
    otra.write_text("a,b\n1,2\n", encoding="utf-8")
    with pytest.raises(PaqueteError, match="deckard"):
        armar_paquete(_planilla(tmp_path / "hoja.csv"), otra, tmp_path / "s")


def test_cli_sale_con_1_si_falta_vincular(tmp_path):
    notas = _notas(tmp_path / "n", [("Juan Pérez", "7", "no"), ("TP0-x", "8", "no")])
    res = runner.invoke(app, ["moodle", "paquete", "--planilla", str(_planilla(tmp_path / "hoja.csv")),
                              "--notas", str(notas), "-o", str(tmp_path / "s")])
    assert res.exit_code == 1 and "TP0-x" in res.output
    assert (tmp_path / "s" / "planilla_moodle.csv").is_file()
