"""fuzz-gen — Generador docente de casos límite por fuzzing (nuevas.md §3.3).

Toma la solución modelo de la cátedra y produce pares ``caso_NN.in`` /
``caso_NN.out`` endurecidos:

1. **Semillas extremas deterministas** por tipo de entrada (enteros con
   INT_MAX/INT_MIN/negativos/cero, cadenas vacías y gigantes, listas) —
   funcionan sin ninguna dependencia externa.
2. **Fuzzing guiado por cobertura** (opcional): si ``clang`` con libFuzzer está
   disponible se compila el modelo instrumentado y se mina el corpus resultante.
3. Para cada candidato se ejecuta el modelo para obtener la salida esperada;
   los duplicados (entrada o salida idéntica, o entradas a distancia
   Levenshtein < 3) se descartan.

El resultado es un banco de testcases listo para la convención de cátedra
(``tests/caso_NN.in/.out``), consumible por ripley/verificar/alucarD.
"""

from __future__ import annotations

import itertools
import random
import re
import shutil
import os
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Sequence


# ---------------------------------------------------------------------------
# Semillas extremas por tipo de parámetro
# ---------------------------------------------------------------------------

EXTREMOS_INT = [0, 1, -1, 2_147_483_647, -2_147_483_648, 100, -100]
EXTREMOS_CADENA = ["", "a", "ab", "A" * 4096, " ", "\t", "ñandú", "0"]

SEMILLAS_DEFAULT: Dict[str, List[str]] = {
    # Cada semilla es una línea de stdin completa (los programas de cátedra leen
    # valores separados por espacios/saltos).
    "int": [str(v) for v in EXTREMOS_INT],
    "cadena": [f'"{s}"' for s in EXTREMOS_CADENA],
    "dos_int": [f"{a} {b}" for a, b in itertools.product([0, 1, -1, 100], repeat=2)][::7],
    "tres_int": [f"{a} {b} {c}" for a, b, c in
                 itertools.product([-1, 0, 1], [5, 50], [9, 99])][::5],
}


def semillas_por_espec(spec: Optional[dict]) -> List[str]:
    """Genera las semillas iniciales según spec.yaml (o las default)."""
    if not spec:
        espec = {"tipo_entrada": "int"}
    else:
        espec = spec
    tipo = str(espec.get("tipo_entrada", "int")).lower()
    claves = {
        "int": ["int"],
        "cadena": ["cadena"],
        "dos_int": ["dos_int"],
        "tres_int": ["tres_int"],
        "lista": ["lista"],
    }
    clave = claves.get(tipo, ["int"])[0]
    semillas = list(SEMILLAS_DEFAULT.get(clave, SEMILLAS_DEFAULT["int"]))
    if clave == "lista":
        n = int(espec.get("tamano_max", 10))
        semillas += ["", " ".join(["7"] * 1), " ".join(["42"] * n),
                     " ".join(["-5", "0", "5"]),
                     " ".join(str(2_147_483_647) for _ in range(min(n, 8)))]
    extra = espec.get("semillas_extra") or []
    semillas.extend(str(e) for e in extra)
    return semillas


def mutar(semilla: str, rng: random.Random) -> str:
    """Muta una semilla: recorte, repetición de tokens, números extremos."""
    tokens = semilla.split() or [""]
    operacion = rng.choice(["recortar", "repetir", "extremo", "negativo", "swap"])
    if operacion == "recortar" and len(tokens) > 1:
        return " ".join(tokens[: max(1, len(tokens) // 2)])
    if operacion == "repetir":
        return " ".join(tokens + tokens[-1:])
    if operacion == "extremo" and tokens:
        idx = rng.randrange(len(tokens))
        tokens[idx] = rng.choice(["2147483647", "-2147483648", "0"])
        return " ".join(tokens)
    if operacion == "negativo" and tokens:
        idx = rng.randrange(len(tokens))
        try:
            tokens[idx] = str(-abs(int(tokens[idx])))
        except ValueError:
            tokens[idx] = "-" + tokens[idx]
        return " ".join(tokens)
    if len(tokens) >= 2:
        i, j = rng.sample(range(len(tokens)), 2)
        tokens[i], tokens[j] = tokens[j], tokens[i]
    return " ".join(tokens)


# ---------------------------------------------------------------------------
# Utilidades de texto
# ---------------------------------------------------------------------------

def distancia_levenshtein(a: str, b: str) -> int:
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    previa = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        actual = [i]
        for j, cb in enumerate(b, 1):
            actual.append(min(previa[j] + 1, actual[j - 1] + 1,
                              previa[j - 1] + (ca != cb)))
        previa = actual
    return previa[-1]


def normalizar_salida(s: str) -> str:
    return "\n".join(linea.strip() for linea in s.strip().replace("\r\n", "\n").split("\n"))


def son_casi_iguales(a: str, b: str, umbral: int = 3) -> bool:
    return distancia_levenshtein(a, b) < umbral


# ---------------------------------------------------------------------------
# Compilación y ejecución del modelo
# ---------------------------------------------------------------------------

def compilar_modelo(fuente: Path, salida: Path,
                    con_libfuzzer: bool = False) -> tuple[bool, str, bool]:
    """Compila el modelo. Devuelve (ok, stderr, uso_libfuzzer).

    Con libFuzzer sólo si clang está disponible y ``con_libfuzzer=True``; si no,
    compila con gcc clásico (modo determinista).
    """
    clang = shutil.which("clang")
    if con_libfuzzer and clang:
        cmd = [clang, "-g", "-O1", "-fsanitize=fuzzer,address",
               "-fno-omit-frame-pointer", "-o", str(salida), str(fuente), "-lm"]
        usa_fuzzer = True
    else:
        gcc = shutil.which("gcc")
        if gcc is None:
            return False, "gcc no disponible", False
        cmd = [gcc, "-std=c11", "-O2", "-Wall", "-o", str(salida), str(fuente), "-lm"]
        usa_fuzzer = False
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    except subprocess.TimeoutExpired:
        return False, "compilación excedió el timeout", usa_fuzzer
    return proc.returncode == 0, proc.stderr[-800:], usa_fuzzer


def ejecutar_modelo(binario: Path, entrada: str,
                    timeout: float = 5.0) -> tuple[int, str]:
    """Corre el modelo con `entrada` en stdin. Devuelve (returncode, stdout)."""
    try:
        proc = subprocess.run([str(binario)], input=entrada.encode(),
                              capture_output=True, timeout=timeout)
        return proc.returncode, proc.stdout.decode("utf-8", errors="replace")
    except subprocess.TimeoutExpired:
        return 124, ""
    except OSError as e:
        return 127, str(e)


# ---------------------------------------------------------------------------
# Minería LibFuzzer (opcional)
# ---------------------------------------------------------------------------

def minar_corpus_libfuzzer(binario: Path, corpus_dir: Path, segundos: int = 15,
                           workers: int = 0) -> List[str]:
    """Ejecuta libFuzzer unos segundos y devuelve las entradas del corpus."""
    if shutil.which(binario.name, path=str(binario.parent)) is None and not binario.exists():
        return []
    corpus_out = corpus_dir.parent / "corpus_minado"
    corpus_out.mkdir(parents=True, exist_ok=True)
    try:
        subprocess.run(
            [str(binario), str(corpus_out), str(corpus_dir),
             f"-max_total_time={segundos}",
             f"-workers={workers or max(1, (os.cpu_count() or 2) - 1)}",
             "-max_len=1024", "-print_final_stats=1"],
            capture_output=True, text=True, timeout=segundos + 30,
        )
    except (subprocess.TimeoutExpired, OSError):
        pass
    candidatos: List[str] = []
    for archivo in sorted(corpus_out.iterdir()):
        try:
            crudo = archivo.read_bytes()
            texto = crudo.decode("utf-8", errors="replace").rstrip("\n")
            if texto and all(ch.isprintable() or ch in "\t " for ch in texto):
                candidatos.append(texto)
        except OSError:
            continue
    return candidatos


# ---------------------------------------------------------------------------
# Orquestación principal
# ---------------------------------------------------------------------------

@dataclass
class ResultadoFuzzGen:
    generados: List[tuple[Path, Path]] = field(default_factory=list)
    descartados_duplicados: int = 0
    crashes: List[str] = field(default_factory=list)
    modo: str = "determinista"


def generar_testcases(fuente_modelo: Path, dir_salida: Path,
                      spec: Optional[dict] = None,
                      cantidad_maxima: int = 20,
                      usar_libfuzzer: bool = True,
                      segundos_fuzz: int = 15) -> ResultadoFuzzGen:
    """Pipeline completo: semillas → mutaciones → (fuzzing opcional) → pares .in/.out."""
    resultado = ResultadoFuzzGen()
    dir_salida.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="dredd_fuzzgen_") as td:
        tmp = Path(td)
        binario = tmp / "modelo.bin"
        ok, err, usa_libfuzzer = compilar_modelo(fuente_modelo, binario,
                                                 con_libfuzzer=usar_libfuzzer)
        if not ok:
            raise RuntimeError(f"No se pudo compilar el modelo: {err}")
        resultado.modo = "libfuzzer" if (usa_libfuzzer and shutil.which("clang")) else "determinista"

        # 1. semillas
        candidatos: List[str] = []
        vistos_in: List[str] = []

        def agregar(candidato: str) -> None:
            candidato = candidato.strip()
            if not candidato:
                return
            if any(son_casi_iguales(candidato, v) for v in vistos_in):
                resultado.descartados_duplicados += 1
                return
            vistos_in.append(candidato)
            candidatos.append(candidato)

        for semilla in semillas_por_espec(spec):
            agregar(semilla)

        # 2. mutaciones deterministas acotadas
        rng = random.Random(20260825)
        base_mutacion = candidatos[:]
        for semilla in base_mutacion:
            for _ in range(4):
                agregar(mutar(semilla, rng))

        # 3. fuzzing guiado (opcional)
        if resultado.modo == "libfuzzer":
            corpus = tmp / "corpus"
            corpus.mkdir()
            for i, c in enumerate(candidatos):
                (corpus / f"seed_{i:03d}.in").write_text(c + "\n", encoding="utf-8")
            minados = minar_corpus_libfuzzer(binario, corpus, segundos=segundos_fuzz)
            for m in minados:
                agregar(m)

        # 4. correr modelo → pares .in/.out con dedupe de salidas
        salidas_vistas: List[str] = []
        numero = 1
        for candidato in candidatos:
            rc, salida = ejecutar_modelo(binario, candidato + "\n")
            salida_norm = normalizar_salida(salida)
            if rc == 124:
                resultado.crashes.append(f"timeout con entrada: {candidato!r:.60}")
                continue
            if rc != 0:
                resultado.crashes.append(
                    f"el modelo terminó con rc={rc} ante: {candidato!r:.60}")
                continue
            if any(salida_norm == s for s in salidas_vistas):
                resultado.descartados_duplicados += 1
                continue
            salidas_vistas.append(salida_norm)

            in_path = dir_salida / f"caso_{numero:02d}.in"
            out_path = dir_salida / f"caso_{numero:02d}.out"
            in_path.write_text(candidato + "\n", encoding="utf-8")
            out_path.write_text(salida if salida.endswith("\n") else salida + "\n",
                                encoding="utf-8")
            resultado.generados.append((in_path, out_path))
            numero += 1
            if len(resultado.generados) >= cantidad_maxima:
                break

    return resultado
