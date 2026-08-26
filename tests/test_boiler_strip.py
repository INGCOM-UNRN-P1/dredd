"""Pruebas de boiler-strip: sanitización de plantilla antes del Winnowing."""

from dredd.core.boiler_strip import BoilerStripper, strip_template
from dredd.core.plagiarism import PlagiarismDetector

PLANTILLA = '''#include <stdio.h>
#include <stdlib.h>
#define MAX_ALUMNOS 100

typedef struct {
    int legajo;
    float nota;
} Alumno;
'''


def _preparar(tmp_path, cuerpo_a: str, cuerpo_b: str):
    plantilla = tmp_path / "plantilla.c"
    plantilla.write_text(PLANTILLA, encoding="utf-8")
    entregas = tmp_path / "submissions"
    for alumno, cuerpo in (("alumno_a", cuerpo_a), ("alumno_b", cuerpo_b)):
        d = entregas / alumno
        d.mkdir(parents=True)
        (d / "main.c").write_text(PLANTILLA + "\n" + cuerpo, encoding="utf-8")
    return plantilla, entregas


def test_sanitizador_elimina_ventanas_de_plantilla(tmp_path):
    plantilla = tmp_path / "p.c"
    plantilla.write_text(PLANTILLA, encoding="utf-8")

    stripper = BoilerStripper(ventanas_minimas=2)
    stripper.cargar_plantilla(plantilla)

    codigo = PLANTILLA + "\nfloat especial(void) { return 42.0f; }\n"
    limpio = stripper.limpiar(codigo)

    assert "/* boilerplate */" in limpio
    assert "#define MAX_ALUMNOS" not in limpio
    assert "especial" in limpio


def test_linea_casual_no_se_elimina(tmp_path):
    plantilla = tmp_path / "p.c"
    plantilla.write_text("#include <stdio.h>\n", encoding="utf-8")  # 1 línea sola

    stripper = BoilerStripper(ventanas_minimas=2)
    stripper.cargar_plantilla(plantilla)

    # una única línea coincidente no debe borrarse (ventana mínima = 2)
    codigo = "#include <stdio.h>\nint unico(void){return 7;}\n"
    assert "#include <stdio.h>" in stripper.limpiar(codigo)


def _similitud_cruda(detector, entregas):
    fps = {d.name: detector.extract_fingerprints_from_dir(d)
           for d in sorted(entregas.iterdir()) if d.is_dir()}
    a, b = list(fps.values())
    if not a or not b:
        return 0.0
    return 2.0 * len(a & b) / (len(a) + len(b))


def test_strip_reduce_similitud_entre_alumnos_distintos(tmp_path):
    plantilla, entregas = _preparar(
        tmp_path,
        "float criterio_a(float x) { return x * 3.0f; }\n",
        "int criterio_b(int n) { return n - 1; }\n",
    )

    sim_sin = _similitud_cruda(PlagiarismDetector(), entregas)
    sim_con = _similitud_cruda(PlagiarismDetector(plantilla=plantilla), entregas)

    # la plantilla compartida genera solapamiento artificial...
    assert sim_sin > 0.10, f"la plantilla debe inflar la similitud cruda ({sim_sin:.2f})"
    # ...y boiler-strip debe reducirla al menos a la mitad
    assert sim_con <= sim_sin / 2, (f"cruda={sim_sin:.2f} sanitizada={sim_con:.2f}")


def test_strip_template_devuelve_por_alumno(tmp_path):
    plantilla, entregas = _preparar(
        tmp_path,
        "int a_especial(void) { return 1; }\n",
        "int b_especial(void) { return 2; }\n",
    )
    resultados = strip_template(entregas, plantilla)
    assert set(resultados) == {"alumno_a", "alumno_b"}
    assert "/* boilerplate */" in resultados["alumno_b"]
