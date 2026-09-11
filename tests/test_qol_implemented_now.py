"""Tests automatizados para las mejoras QoL implementadas ahora en Dredd."""

from datetime import datetime, timezone, timedelta
from pathlib import Path
import subprocess
import pytest
from typer.testing import CliRunner

from dredd.cli import app
from dredd.core.late_penalty import calcular_penalizacion_entrega
from dredd.core.makefile_audit import auditar_makefile
from dredd.core.submission_typology import clasificar_tipologia_entrega, TipoEntrega
from dredd.core.stability_eval import evaluar_estabilidad_binario
from dredd.core.cohort_bench import comparar_desempeno_cohorte, medir_ejecucion_individual
from dredd.core.smith_adversary import (
    inyectar_casos_adversarios,
    evaluar_con_casos_adversarios,
    CASOS_ADVERSARIOS_ESTANDAR,
)
from dredd.core.sandbox import execute_shielded_sandbox

runner = CliRunner()


def test_late_penalty_on_time_and_grace():
    limite = datetime(2026, 4, 1, 23, 59, tzinfo=timezone.utc)
    # A tiempo
    entrega_ok = datetime(2026, 4, 1, 22, 0, tzinfo=timezone.utc)
    res_ok = calcular_penalizacion_entrega(entrega_ok, limite, nota_original=10.0)
    assert res_ok.a_tiempo is True
    assert res_ok.puntos_descuento == 0.0
    assert res_ok.nota_final == 10.0

    # Dentro de los 15 minutos de gracia
    entrega_gracia = limite + timedelta(minutes=10)
    res_gracia = calcular_penalizacion_entrega(entrega_gracia, limite, nota_original=10.0, gracia_minutos=15)
    assert res_gracia.a_tiempo is True
    assert res_gracia.puntos_descuento == 0.0


def test_late_penalty_delayed_and_cap():
    limite = datetime(2026, 4, 1, 23, 59, tzinfo=timezone.utc)
    # Retraso de 4 horas y 15 minutos (4 horas efectivas con 15m gracia) -> 4 * 0.5 = 2.0 puntos
    entrega_tarde = limite + timedelta(hours=4, minutes=15)
    res_tarde = calcular_penalizacion_entrega(
        entrega_tarde, limite, nota_original=8.0, gracia_minutos=15, puntos_por_hora=0.5, max_descuento=3.0
    )
    assert res_tarde.a_tiempo is False
    assert res_tarde.puntos_descuento == 2.0
    assert res_tarde.nota_final == 6.0

    # Retraso extremo de 3 días con tope
    entrega_muy_tarde = limite + timedelta(days=3)
    res_tope = calcular_penalizacion_entrega(
        entrega_muy_tarde, limite, nota_original=10.0, max_descuento=4.0
    )
    assert res_tope.puntos_descuento == 4.0
    assert res_tope.nota_final == 6.0


def test_cli_late_penalty():
    res = runner.invoke(app, [
        "late-penalty",
        "2026-04-02 02:30",
        "2026-04-01 23:59",
        "--nota", "9.5",
        "--tasa", "0.5",
    ])
    assert res.exit_code == 0
    assert "Dredd Late Penalty Calculator" in res.stdout
    assert "Fuera de término" in res.stdout


def test_makefile_audit_cheats_and_unauthorized_libs(tmp_path: Path):
    mk_file = tmp_path / "Makefile"
    mk_file.write_text("""CC = gcc
CFLAGS = -Wall -Wextra -w
LDFLAGS = -lm -lcurl

all: main

main: main.o
\t$(CC) main.o -o main $(LDFLAGS) || true
\tcp /tmp/precompiled.o .

clean:
\trm -f main *.o
""", encoding="utf-8")

    findings = auditar_makefile(mk_file)
    reglas = {f.regla for f in findings}
    assert "MK_DISABLE_WARNINGS" in reglas
    assert "MK_UNAUTHORIZED_LIB" in reglas
    assert "MK_MASK_ERRORS" in reglas
    assert "MK_PRECOMPILED_COPY" in reglas

    # CLI test
    res_cli = runner.invoke(app, ["audit-makefile", str(mk_file)])
    assert res_cli.exit_code == 0
    assert "Auditoría de Makefile" in res_cli.stdout


def test_submission_typology_monolithic_vs_modular(tmp_path: Path):
    # Caso 1: Monolítica
    dir_mono = tmp_path / "alumno_mono"
    dir_mono.mkdir()
    (dir_mono / "main.c").write_text("int main(void) { return 0; }\n", encoding="utf-8")
    rep_mono = clasificar_tipologia_entrega(dir_mono)
    assert rep_mono.tipologia == TipoEntrega.MONOLITICA
    assert rep_mono.tiene_main is True
    assert rep_mono.cant_c == 1

    # Caso 2: Modular
    dir_mod = tmp_path / "alumno_mod"
    dir_mod.mkdir()
    (dir_mod / "main.c").write_text('#include "util.h"\nint main(void) { return 0; }\n', encoding="utf-8")
    (dir_mod / "util.c").write_text('#include "util.h"\nvoid util(void){}\n', encoding="utf-8")
    (dir_mod / "util.h").write_text("void util(void);\n", encoding="utf-8")
    rep_mod = clasificar_tipologia_entrega(dir_mod)
    assert rep_mod.tipologia == TipoEntrega.MODULAR
    assert rep_mod.cant_c == 2
    assert rep_mod.cant_h == 1

    # CLI test
    res_cli = runner.invoke(app, ["typology", str(dir_mod)])
    assert res_cli.exit_code == 0
    assert "MODULAR" in res_cli.stdout


def test_stability_eval_deterministic_binary(tmp_path: Path):
    # Compilar un binario determinista
    src = tmp_path / "prog.c"
    src.write_text("""#include <stdio.h>
int main(void) {
    printf("Resultado fijo: 42\\n");
    return 0;
}
""", encoding="utf-8")
    bin_p = tmp_path / "prog_bin"
    subprocess.run(["gcc", str(src), "-o", str(bin_p)], check=True)

    res = evaluar_estabilidad_binario(bin_p, repeticiones=4)
    assert res.estable is True
    assert res.salidas_distintas == 1
    assert res.total_corridas == 4
    assert res.codigos_retorno == [0, 0, 0, 0]

    # CLI invocation
    res_cli = runner.invoke(app, ["eval-stability", str(bin_p), "--repeticiones", "3"])
    assert res_cli.exit_code == 0
    assert "SÍ (100% Determinista)" in res_cli.stdout


def test_cohort_bench(tmp_path: Path):
    entregas = tmp_path / "entregas"
    entregas.mkdir()

    # Alumno A
    a_dir = entregas / "alumno_a"
    a_dir.mkdir()
    src_a = a_dir / "main.c"
    src_a.write_text("int main(void) { return 0; }\n", encoding="utf-8")
    subprocess.run(["gcc", str(src_a), "-o", str(a_dir / "main")], check=True)

    # Alumno B
    b_dir = entregas / "alumno_b"
    b_dir.mkdir()
    src_b = b_dir / "main.c"
    src_b.write_text("""#include <unistd.h>
int main(void) { usleep(10000); return 0; }
""", encoding="utf-8")
    subprocess.run(["gcc", str(src_b), "-o", str(b_dir / "main")], check=True)

    report = comparar_desempeno_cohorte(entregas, nombre_binario="main")
    assert report.total_evaluados == 2
    assert report.alumnos_exitosos == 2
    assert len(report.ranking) == 2

    # CLI test
    res_cli = runner.invoke(app, ["cohort-bench", str(entregas), "--bin", "main"])
    assert res_cli.exit_code == 0
    assert "Benchmarking de Cohorte" in res_cli.stdout
    assert "alumno_a" in res_cli.stdout


def test_smith_adversary(tmp_path: Path):
    tests_dir = tmp_path / "tests"
    rutas = inyectar_casos_adversarios(tests_dir)
    assert len(rutas) == len(CASOS_ADVERSARIOS_ESTANDAR)
    assert (tests_dir / "adv_int_overflow.in").is_file()

    # Compilar un programa seguro que maneja enteros
    src = tmp_path / "eco.c"
    src.write_text("""#include <stdio.h>
int main(void) {
    long x;
    if (scanf("%ld", &x) == 1) {
        printf("Leido: %ld\\n", x);
    }
    return 0;
}
""", encoding="utf-8")
    bin_p = tmp_path / "eco_bin"
    subprocess.run(["gcc", str(src), "-o", str(bin_p)], check=True)

    rep = evaluar_con_casos_adversarios(bin_p)
    assert rep.crashes == 0
    assert rep.casos_superados == rep.total_casos

    # CLI test
    res_cli = runner.invoke(app, ["smith-adversary", str(bin_p)])
    assert res_cli.exit_code == 0
    assert "Resultados de Pruebas Adversarias" in res_cli.stdout


def test_execute_shielded_sandbox():
    retcode, out, err, timed_out = execute_shielded_sandbox(["echo", "blindado"], timeout=2.0)
    assert retcode == 0
    assert "blindado" in out
    assert timed_out is False
