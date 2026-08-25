"""Pruebas de fuzz-gen: semillas, mutaciones, dedupe y generación end-to-end."""

from pathlib import Path

from dredd.core.fuzz_gen import (
    distancia_levenshtein,
    generar_testcases,
    mutar,
    normalizar_salida,
    son_casi_iguales,
    semillas_por_espec,
)


MODELO = '''#include <stdio.h>
int main(void) {
    int a, b;
    if (scanf("%d %d", &a, &b) != 2) return 1;
    printf("%d\\n", a > b ? a : b);
    return 0;
}
'''


def test_semillas_int_incluye_extremos():
    semillas = semillas_por_espec({"tipo_entrada": "int"})
    assert "2147483647" in semillas
    assert "-2147483648" in semillas
    assert "0" in semillas


def test_semillas_dos_int_y_lista():
    assert any(len(s.split()) == 2 for s in semillas_por_espec({"tipo_entrada": "dos_int"}))
    lista = semillas_por_espec({"tipo_entrada": "lista", "tamano_max": 6})
    assert any(s.count("42") == 6 for s in lista)


def test_mutaciones_mantienen_formato_token():
    rng = __import__("random").Random(1)
    for _ in range(50):
        m = mutar("10 -20 30", rng)
        assert all(t.lstrip("-").isdigit() or t == "-0" for t in m.split()), m


def test_levenshtein_y_casi_iguales():
    assert distancia_levenshtein("casa", "casa") == 0
    assert distancia_levenshtein("gato", "pato") == 1
    assert son_casi_iguales("1234", "1235", umbral=3)
    assert son_casi_iguales("1000000", "2000000", umbral=3)  # distan 1
    assert not son_casi_iguales("1000000", "999999999", umbral=3)


def test_normalizar_salida_quita_espacios_finales():
    assert normalizar_salida("hola\r\n mundo \n") == "hola\nmundo"


def test_generacion_end_to_end(tmp_path):
    modelo = tmp_path / "modelo.c"
    modelo.write_text(MODELO)
    salida = tmp_path / "casos"

    resultado = generar_testcases(modelo, salida,
                                  spec={"tipo_entrada": "dos_int"},
                                  cantidad_maxima=8,
                                  usar_libfuzzer=False)

    pares = resultado.generados
    assert len(pares) >= 2, "debe generar al menos un par usable"
    for in_p, out_p in pares:
        tokens = in_p.read_text().split()
        assert len(tokens) == 2
        esperado = out_p.read_text().strip()
        a, b = map(int, tokens)
        assert esperado == str(max(a, b))
    # modo determinista sin clang
    assert resultado.modo == "determinista"


def test_generacion_reporta_rechazos_del_modelo(tmp_path):
    modelo = tmp_path / "estricto.c"
    modelo.write_text(
        "#include <stdio.h>\n"
        "int main(void){\n"
        '    int a, b;\n'
        '    if (scanf("%d %d", &a, &b) != 2) return 1;\n'
        "    if (a < 0 || b < 0) return 2;   // dominio restringido\n"
        '    printf("%d\\n", a + b);\n'
        "    return 0;\n"
        "}\n"
    )
    resultado = generar_testcases(modelo, tmp_path / "casos",
                                  spec={"tipo_entrada": "dos_int"},
                                  cantidad_maxima=8,
                                  usar_libfuzzer=False)
    # las semillas/mutaciones con negativos deben aparecer como rechazos del modelo
    assert any("rc=2" in c for c in resultado.crashes), resultado.crashes
    assert resultado.generados, "y también debe haber casos válidos"
