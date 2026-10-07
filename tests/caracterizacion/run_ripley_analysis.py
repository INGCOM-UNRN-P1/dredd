"""Caracterización de `run_ripley_analysis` (N-ECO-16): escenarios, dobles y generación del golden.

La función orquesta una docena de colaboradores (guía, configuración, binarios, base de metadatos,
línea base, ripley o el linter AST, daedalus o make, kaneda, casos de prueba, gaff y spunkmeyer). Cada
escenario arma una entrega en un directorio temporal, reemplaza los colaboradores por dobles que
registran sus llamadas y devuelven valores fijos, y guarda el resultado junto con la secuencia de
llamadas. golden_run_ripley_analysis.json se generó antes de partir la función de 514 líneas; regenerarlo
solo ante un cambio de comportamiento intencional:

    uv run python tests/caracterizacion/run_ripley_analysis.py
"""

from __future__ import annotations

import json
import subprocess
import tempfile
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Iterator
from unittest import mock

AQUI = Path(__file__).resolve().parent
GOLDEN = AQUI / "golden_run_ripley_analysis.json"

PROGRAMA = "int main(void)\n{\n    return 0;\n}\n"


def _checks(**cambios: Any) -> SimpleNamespace:
    base = dict(ripley_enabled=True, kaneda_enabled=True, gaff_enabled=True, spunkmeyer_enabled=True,
                ripley_rules=[], ripley_disabled_rules=[], daedalus_compiler="gcc")
    base.update(cambios)
    return SimpleNamespace(**base)


# Cada escenario: archivos de la entrega, argumentos y cómo responden los dobles.
ESCENARIOS: dict[str, dict[str, Any]] = {
    "individuales_completo": dict(
        archivos={"main.c": PROGRAMA, "falla.c": "int main(void) { return x; }\n",
                  "sistema.c": "#include <stdlib.h>\nint main(void) { system(\"ls\"); }\n",
                  "ej2/sin_hacer.c": PROGRAMA, ".oculto/y.c": PROGRAMA, "vendor/v.c": PROGRAMA,
                  ".deckard/guia.toml": "", ".metadata.db": ""},
        kwargs=dict(activity_slug="tp1"),
        modo="archivos_individuales",
        checks=_checks(ripley_rules=["0x0001h"], ripley_disabled_rules=["0x1002h"]),
        guia=SimpleNamespace(tipo_entrega="archivos_individuales", exercises=["ej1"]),
        sin_hacer=["ej2"],
        ignorados=[{"reason": "ERROR_BINARY: ELF", "filename": "a.out"},
                   {"reason": "ERROR_BINARY: PE", "filename": "tp.exe"},
                   {"reason": None, "filename": "notas.txt"}],
    ),
    "individuales_sin_fuentes": dict(
        archivos={"leeme.txt": "nada"},
        kwargs=dict(guide=SimpleNamespace(tipo_entrega=None, exercises=[])),
        modo="archivos_individuales",
        checks=_checks(kaneda_enabled=False),
    ),
    "individuales_con_ripley": dict(
        archivos={"main.c": PROGRAMA, "otro.c": PROGRAMA, ".metadata.db": ""},
        kwargs=dict(activity_slug="tp2", workspace_dir="__ws__"),
        modo="archivos_individuales",
        checks=_checks(ripley_rules=["all"], kaneda_enabled=False, gaff_enabled=False, spunkmeyer_enabled=False),
        ripley_cli=True,
        casos_locales=True,
        db_rota=True,
    ),
    "individuales_ripley_falla": dict(
        archivos={"main.c": PROGRAMA},
        kwargs=dict(activity_slug="tp3"),
        modo="archivos_individuales",
        checks=_checks(gaff_enabled=False),
        ripley_cli="falla",
    ),
    "individuales_ripley_json_roto": dict(
        archivos={"main.c": PROGRAMA, "explota.c": PROGRAMA, "r1/x.c": PROGRAMA},
        kwargs=dict(activity_slug="tp4"),
        modo="archivos_individuales",
        checks=_checks(gaff_enabled=False, spunkmeyer_enabled=False),
        ripley_cli="json_roto",
    ),
    "individuales_minimo": dict(
        archivos={"main.c": PROGRAMA, ".metadata.db": ""},
        kwargs=dict(guide=SimpleNamespace(tipo_entrega=None, exercises=["e1"])),
        modo="archivos_individuales",
        checks=_checks(kaneda_enabled=False, gaff_enabled=False, spunkmeyer_enabled=False),
        ripley_cli="vacio",
        sin_revision=True,
        guia_sin_casos=True,
        sin_binarios=True,
    ),
    "individuales_sin_ripley": dict(
        archivos={"main.c": PROGRAMA},
        kwargs=dict(checks_override=_checks(ripley_enabled=False, kaneda_enabled=False), baseline_dir="__base__"),
        modo="archivos_individuales",
        checks=_checks(),
    ),
    "makefiles_con_resultados": dict(
        archivos={"ej1/main.c": PROGRAMA, "ej1/Makefile": "all:\n", "ej2/main.c": PROGRAMA, "ej2/Makefile": "all:\n"},
        kwargs=dict(tipo_entrega="makefiles_individuales"),
        modo="makefiles_individuales",
        checks=_checks(kaneda_enabled=False),
        makefiles=[("ej1", True, True, "ok ej1"), ("ej2", True, False, "falló ej2")],
    ),
    "makefiles_makefile_raiz": dict(
        archivos={"main.c": PROGRAMA, "Makefile": "all:\n"},
        kwargs=dict(tipo_entrega="makefiles_individuales"),
        modo="makefiles_individuales",
        checks=_checks(kaneda_enabled=False),
    ),
    "makefiles_nada": dict(
        archivos={"main.c": PROGRAMA},
        kwargs=dict(tipo_entrega="makefiles_individuales"),
        modo="makefiles_individuales",
        checks=_checks(kaneda_enabled=False, gaff_enabled=False),
    ),
    "proyecto_test_ok": dict(
        archivos={"main.c": PROGRAMA, "Makefile": "all:\ntest:\n"},
        kwargs=dict(tipo_entrega="proyecto"),
        modo="proyecto",
        checks=_checks(kaneda_enabled=False),
        make_test=(0, "todo bien", ""),
    ),
    "proyecto_sin_target_test": dict(
        archivos={"main.c": PROGRAMA, "Makefile": "all:\n"},
        kwargs=dict(tipo_entrega="proyecto"),
        modo="proyecto",
        checks=_checks(kaneda_enabled=False),
        make_test=(2, "", "make: *** No rule to make target 'test'.  Stop."),
    ),
    "proyecto_test_falla_con_guia": dict(
        archivos={"main.c": PROGRAMA, "sistema.c": "int f(void) { return system(\"x\"); }\n", "Makefile": "all:\n"},
        kwargs=dict(tipo_entrega="proyecto", guide=SimpleNamespace(tipo_entrega="proyecto", exercises=["e1"])),
        modo="proyecto",
        checks=_checks(),
        make_test=(2, "", "assert falló\n" * 80),
        compila_make=False,
    ),
    "proyecto_plantilla_tp_por_suite": dict(
        archivos={"main.c": PROGRAMA, "Makefile": "all:\ntest:\n", "libs/cadenas/Makefile": "test:\n",
                  "libs/p1_test/Makefile": "test:\n", "ejercicios/ejercicio1/Makefile": "test:\n"},
        kwargs=dict(tipo_entrega="proyecto"),
        modo="proyecto",
        checks=_checks(kaneda_enabled=False),
        make_test=(2, "Compilando…\n", "[FALLO] prueba.c:7: ASSERT_INT_EQ(3, 4)"),
    ),
    "proyecto_make_test_explota": dict(
        archivos={"main.c": PROGRAMA, "Makefile": "all:\n"},
        kwargs=dict(tipo_entrega="proyecto"),
        modo="proyecto",
        checks=_checks(kaneda_enabled=False),
        make_test="excepcion",
    ),
}


class _Registro:
    def __init__(self, raiz: Path) -> None:
        self.raiz = raiz
        self.llamadas: list[list[Any]] = []

    def normalizar(self, valor: Any) -> Any:
        if isinstance(valor, Path):
            valor = str(valor)
        if isinstance(valor, str):
            return valor.replace(str(self.raiz), "<entrega>").replace(str(self.raiz.parent), "<tmp>")
        if isinstance(valor, (list, tuple)):
            return [self.normalizar(v) for v in valor]
        if isinstance(valor, (set, frozenset)):
            return sorted(self.normalizar(v) for v in valor)
        if isinstance(valor, dict):
            return {str(k): self.normalizar(v) for k, v in valor.items()}
        if isinstance(valor, SimpleNamespace):
            return {"namespace": self.normalizar(vars(valor))}
        return valor

    def anotar(self, nombre: str, *args: Any, **kwargs: Any) -> None:
        self.llamadas.append([nombre, self.normalizar(list(args)), self.normalizar(kwargs)])


@contextmanager
def _dobles(esc: dict[str, Any], reg: _Registro) -> Iterator[None]:
    checks = esc["checks"]

    class Configuracion:
        def get_effective_checks(self, slug: Any) -> Any:
            reg.anotar("get_effective_checks", slug)
            return checks

        def get_delivery_mode(self, **kwargs: Any) -> str:
            reg.anotar("get_delivery_mode", **kwargs)
            return esc["modo"]

    configuraciones = iter([None, Configuracion()])

    def load_dredd_config(ruta: Path) -> Any:
        reg.anotar("load_dredd_config", ruta)
        return next(configuraciones)

    def load_guide_from_deckard_dir(ruta: Path) -> Any:
        reg.anotar("load_guide_from_deckard_dir", ruta)
        return esc.get("guia")

    def load_activity_guide(ruta: Path, slug: str, ws: Any) -> Any:
        reg.anotar("load_activity_guide", ruta, slug, ws)
        return None

    def audit_and_purge_binaries_from_dir(ruta: Path) -> list[dict[str, Any]]:
        reg.anotar("audit_and_purge_binaries_from_dir", ruta)
        if esc.get("sin_binarios"):
            return []
        return [{"rule_code": "0x000Fh", "file": "a.out", "line": 1, "severity": "ERROR", "message": "binario"}]

    class DatabaseManager:
        def __init__(self, ruta: Path) -> None:
            reg.anotar("DatabaseManager", ruta)
            if esc.get("db_rota"):
                raise RuntimeError("base corrupta")

        def get_latest_revision(self, slug: str) -> dict[str, int]:
            reg.anotar("get_latest_revision", slug)
            return None if esc.get("sin_revision") else {"id": 7}

        def get_ignored_files(self, rev_id: int) -> list[dict[str, Any]]:
            reg.anotar("get_ignored_files", rev_id)
            return esc.get("ignorados", [])

    def find_baseline_dir(ruta: Path, workspace_dir: Any = None) -> Any:
        reg.anotar("find_baseline_dir", ruta, workspace_dir=workspace_dir)
        return "__base_encontrada__"

    def classify_submission_exercises(ruta: Path, baseline_dir: Any = None) -> dict[str, Any]:
        reg.anotar("classify_submission_exercises", ruta, baseline_dir=baseline_dir)
        return {"uncompleted": esc.get("sin_hacer", []), "completed": ["ej1"]}

    def resolve_sibling_cli(nombre: str) -> Any:
        reg.anotar("resolve_sibling_cli", nombre)
        return "/opt/ripley" if esc.get("ripley_cli") else None

    def run(cmd: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        reg.anotar("subprocess.run", cmd, **{k: v for k, v in kwargs.items() if k == "timeout"})
        if cmd[0] == "/opt/ripley":
            if esc["ripley_cli"] == "falla":
                return subprocess.CompletedProcess(cmd, 2, stdout="", stderr="uso")
            if esc["ripley_cli"] == "vacio":
                return subprocess.CompletedProcess(cmd, 0, stdout=json.dumps({"hallazgos": []}), stderr="")
            if esc["ripley_cli"] == "json_roto":
                return subprocess.CompletedProcess(cmd, 1, stdout="{no es json", stderr="")
            hallazgos = [{"code": "0x0001h", "title": "Nombres", "message": "corto", "file": "main.c", "line": 3},
                         {"rule_code": "0x0009h", "severity": "ESTILO", "file": "otro.c"}]
            return subprocess.CompletedProcess(cmd, 1, stdout=json.dumps({"findings": hallazgos}), stderr="")
        if esc.get("make_test") == "excepcion" and cmd[-1] == "clean":
            raise OSError("make no está instalado")
        if cmd[-1] == "test":
            if esc.get("make_test") == "excepcion":
                raise subprocess.TimeoutExpired(cmd, 60)
            codigo, salida, error = esc.get("make_test", (0, "", ""))
            return subprocess.CompletedProcess(cmd, codigo, stdout=salida, stderr=error)
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    def audit_c_file(ruta: Path) -> list[dict[str, Any]]:
        reg.anotar("audit_c_file", ruta)
        if ruta.name == "explota.c":
            raise ValueError("tree-sitter")
        return [{"rule_code": "0x0001h", "rule_name": "Nombres", "file": ruta.name, "line": 1},
                {"rule_code": "0x1002h", "rule_name": "continue", "file": ruta.name, "line": 2},
                {"rule_id": "0x0009H", "rule_name": "Largo", "file": ruta.name, "line": 3}]

    def compile_c_sources(fuentes: list[Path], output_bin: Path) -> SimpleNamespace:
        reg.anotar("compile_c_sources", fuentes, output_bin=output_bin.name)
        exito = "falla" not in fuentes[0].name
        return SimpleNamespace(
            success=exito, raw_stderr="" if exito else "error: x no declarada",
            full_output="" if fuentes[0].name == "main.c" else f"aviso en {fuentes[0].name}",
            raw_stdout="", translated_diagnostics=[] if exito else [{"mensaje": "x no declarada"}],
            compiler_used="gcc", command=["gcc", fuentes[0].name], returncode=0 if exito else 1)

    def compile_with_make(ruta: Path) -> SimpleNamespace:
        reg.anotar("compile_with_make", ruta)
        exito = esc.get("compila_make", True)
        return SimpleNamespace(success=exito, raw_stderr="" if exito else "make: error", raw_stdout="ok",
                               full_output="salida de make", translated_diagnostics=[])

    def evaluate_makefile_exercises(ruta: Path, baseline_dir: Any = None, uncompleted_exercises: Any = None) -> Any:
        reg.anotar("evaluate_makefile_exercises", ruta, baseline_dir=baseline_dir,
                   uncompleted_exercises=uncompleted_exercises)
        return [SimpleNamespace(exercise_name=n, clean_ok=c, test_ok=t, output_log=log)
                for n, c, t, log in esc.get("makefiles", [])]

    def audit_sandbox_evasion(codigo: str, nombre: str) -> list[SimpleNamespace]:
        reg.anotar("audit_sandbox_evasion", nombre)
        if nombre == "explota.c":
            raise UnicodeError("kaneda")
        if "system(" not in codigo:
            return []
        return [SimpleNamespace(rule_code="SEC-SYSTEM", title="system()", severity="ERROR",
                                message="llamada a system", line=2, code_snippet="system(\"ls\")")]

    valgrind_limpio = {"executed": True, "clean": True, "definitely_lost_bytes": 0, "total_errors": 0}
    valgrind_sucio = {"executed": True, "clean": False, "definitely_lost_bytes": 16, "indirectly_lost_bytes": 8,
                      "possibly_lost_bytes": 4, "still_reachable_bytes": 2, "total_errors": 3, "errors": ["fuga"]}

    def evaluate_guide_testcases(ruta: Path, guia: Any, tipo_entrega: Any = None) -> list[dict[str, Any]]:
        reg.anotar("evaluate_guide_testcases", ruta, guia, tipo_entrega=tipo_entrega)
        if esc.get("guia_sin_casos"):
            return []
        return [{"name": "guía 1", "passed": True, "valgrind_report": valgrind_limpio},
                {"name": "guía 2", "passed": False, "valgrind_report": valgrind_sucio},
                {"name": "guía 3", "passed": True, "valgrind_report": {"executed": False}}]

    def discover_and_run_local_testcases(ruta: Path) -> list[dict[str, Any]]:
        reg.anotar("discover_and_run_local_testcases", ruta)
        if not esc.get("casos_locales"):
            return []
        return [{"name": "local / 1.in", "passed": False, "valgrind_report": valgrind_sucio}]

    def audit_style_with_gaff(ruta: Path, checks: Any = None, uncompleted_exercises: Any = None) -> Any:
        reg.anotar("audit_style_with_gaff", ruta, uncompleted_exercises=uncompleted_exercises)
        return [{"codigo": "0x0003h"}], {"violaciones": 1}

    def audit_antipatterns_with_spunkmeyer(ruta: Path, checks: Any = None, uncompleted_exercises: Any = None) -> Any:
        reg.anotar("audit_antipatterns_with_spunkmeyer", ruta, uncompleted_exercises=uncompleted_exercises)
        return [{"id": "malloc-cast"}]

    rc = "dredd.core.ripley_client"
    parches = [
        mock.patch("dredd.core.config.load_dredd_config", load_dredd_config),
        mock.patch("dredd.core.guide_integration.load_guide_from_deckard_dir", load_guide_from_deckard_dir),
        mock.patch("dredd.core.guide_integration.load_activity_guide", load_activity_guide),
        mock.patch("dredd.core.binary_check.audit_and_purge_binaries_from_dir", audit_and_purge_binaries_from_dir),
        mock.patch("dredd.core.db.DatabaseManager", DatabaseManager),
        mock.patch("dredd.core.baseline.find_baseline_dir", find_baseline_dir),
        mock.patch("dredd.core.baseline.classify_submission_exercises", classify_submission_exercises),
        mock.patch("dredd.core.ast_checker.audit_c_file", audit_c_file),
        mock.patch("dredd.core.compiler.compile_with_make", compile_with_make),
        mock.patch("dredd.core.makefile_eval.evaluate_makefile_exercises", evaluate_makefile_exercises),
        mock.patch(f"{rc}.resolve_sibling_cli", resolve_sibling_cli),
        mock.patch(f"{rc}.subprocess.run", run),
        mock.patch(f"{rc}.compile_c_sources", compile_c_sources),
        mock.patch(f"{rc}.audit_sandbox_evasion", audit_sandbox_evasion),
        mock.patch(f"{rc}.evaluate_guide_testcases", evaluate_guide_testcases),
        mock.patch(f"{rc}.discover_and_run_local_testcases", discover_and_run_local_testcases),
        mock.patch(f"{rc}.audit_style_with_gaff", audit_style_with_gaff),
        mock.patch(f"{rc}.audit_antipatterns_with_spunkmeyer", audit_antipatterns_with_spunkmeyer),
    ]
    for parche in parches:
        parche.start()
    try:
        yield
    finally:
        for parche in reversed(parches):
            parche.stop()


def ejecutar(nombre: str) -> dict[str, Any]:
    from dredd.core.ripley_client import run_ripley_analysis

    esc = ESCENARIOS[nombre]
    with tempfile.TemporaryDirectory() as tmp:
        raiz = Path(tmp) / "entrega"
        for relativa, contenido in esc["archivos"].items():
            ruta = raiz / relativa
            ruta.parent.mkdir(parents=True, exist_ok=True)
            ruta.write_text(contenido, encoding="utf-8")
        (raiz / ".deckard").mkdir(exist_ok=True) if ".deckard/guia.toml" in esc["archivos"] else None
        reg = _Registro(raiz)
        kwargs = dict(esc["kwargs"])
        for clave in ("workspace_dir", "baseline_dir"):
            if clave in kwargs:
                kwargs[clave] = raiz.parent / kwargs[clave]
        with _dobles(esc, reg):
            resultado = run_ripley_analysis(raiz, **kwargs)
        return {"resultado": reg.normalizar(resultado), "llamadas": reg.llamadas}


def main() -> None:
    golden = {nombre: ejecutar(nombre) for nombre in ESCENARIOS}
    GOLDEN.write_text(json.dumps(golden, ensure_ascii=False, indent=1, default=str) + "\n", encoding="utf-8")
    print(f"{len(golden)} escenarios, {sum(len(g['llamadas']) for g in golden.values())} llamadas registradas")


if __name__ == "__main__":
    main()
