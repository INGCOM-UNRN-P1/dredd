"""boiler-strip — Sanitizador de plantillas de cátedra para análisis de plagio.

El código provisto por la cátedra (esqueletos, firmas de funciones, Makefile,
includes fijos) infla los falsos positivos del detector Winnowing: todos los
alumnos comparten esos tokens. Este módulo preprocesa cada entrega eliminando
los fragmentos presentes en la plantilla antes de calcular huellas.

Estrategia por líneas normalizadas:
1. Se normaliza cada línea (sin comentarios, espacios colapsados).
2. Se construye un conjunto de "n-gramas de línea" de la plantilla.
3. En el código del alumno, toda ventana consecutiva de líneas que aparezca
   íntegramente en la plantilla se sustituye por una única línea marcadora
   ``/* boilerplate */``, conservando la estructura general (los k-grams que
   rodean código propio siguen comparables).
"""

from __future__ import annotations

import re
from typing import Dict, List  # noqa: F401
from pathlib import Path


def _normalizar_linea(linea: str) -> str:
    sin_comentarios = re.sub(r"//.*$", "", linea)
    return re.sub(r"\s+", " ", sin_comentarios).strip()


def _lineas_significativas(texto: str) -> List[str]:
    """Líneas normalizadas no vacías."""
    lineas = []
    for cruda in texto.splitlines():
        normalizada = _normalizar_linea(cruda)
        if normalizada:
            lineas.append(normalizada)
    return lineas


# ---------------------------------------------------------------------------
# API principal
# ---------------------------------------------------------------------------

class BoilerStripper:
    """Preprocesador que elimina fragmentos de plantilla de entregas."""

    MARCADOR = "/* boilerplate */"

    def __init__(self, ventanas_minimas: int = 2):
        """
        ``ventanas_minimas``: cantidad mínima de líneas consecutivas iguales a
        la plantilla para considerarse boilerplate (evita borrar coincidencias
        casuales de 1 línea).
        """
        self.ventanas_minimas = max(1, ventanas_minimas)
        self._frases: set[frozenset] = set()  # n-gramas de línea de la plantilla
        self._listado: set[tuple] = set()

    def cargar_plantilla(self, ruta: Path | str) -> int:
        """Carga una plantilla (archivo o directorio .c/.h) y devuelve las
        líneas significativas incorporadas."""
        ruta = Path(ruta)
        textos: list[str] = []
        if ruta.is_dir():
            for archivo in sorted(ruta.rglob("*")):
                if archivo.suffix in (".c", ".h") and archivo.is_file():
                    textos.append(archivo.read_text(encoding="utf-8", errors="replace"))
        elif ruta.is_file():
            textos.append(ruta.read_text(encoding="utf-8", errors="replace"))
        else:
            raise FileNotFoundError(f"Plantilla inexistente: {ruta}")

        total = 0
        for texto in textos:
            lineas = _lineas_significativas(texto)
            total += len(lineas)
            self._listado.update(lineas)
        return total

    def limpiar(self, codigo: str) -> str:
        """Elimina ventanas de líneas presentes íntegramente en la plantilla."""
        if not self._listado:
            return codigo

        lineas_norm = [_normalizar_linea(l) for l in codigo.splitlines()]
        salida: list[str] = []
        i = 0
        n = len(lineas_norm)
        while i < n:
            # medir la corrida de líneas-plantilla consecutivas (no vacías)
            j = i
            corrida = 0
            while j < n and lineas_norm[j] and lineas_norm[j] in self._listado:
                corrida += 1
                j += 1

            if corrida >= self.ventanas_minimas:
                salida.append(self.MARCADOR)
                # saltar también las vacías intermedias dentro de la corrida
                while i < j:
                    i += 1
                continue

            # copiar tal cual hasta próxima candidata (líneas originales)
            fin_corrida = j if corrida > 0 else i + 1
            originales = codigo.splitlines()
            salida.extend(originales[k] for k in range(i, min(fin_corrida, n)))
            i = fin_corrida

        # colapsar marcadores consecutivos en uno solo
        colapsado: list[str] = []
        for linea in salida:
            if linea == self.MARCADOR and colapsado and colapsado[-1] == self.MARCADOR:
                continue
            if linea == self.MARCADOR and colapsado and colapsado[-1].strip() == "":
                colapsado.pop()
            colapsado.append(linea)
        return "\n".join(colapsado)


def strip_template(entregas_dir: Path, plantilla: Path | str,
                   ventanas_minimas: int = 2) -> Dict[str, str]:
    """Aplica BoilerStripper a todos los *.c de cada alumno en ``entregas_dir``.

    Devuelve {alumno: código_sanitizado} sin escribir archivos.
    """
    stripper = BoilerStripper(ventanas_minimas=ventanas_minimas)
    stripper.cargar_plantilla(plantilla)

    resultados: Dict[str, str] = {}
    for dir_alumno in sorted(p for p in entregas_dir.iterdir()
                             if p.is_dir() and not p.name.startswith(".")):
        trozos: List[str] = []
        for c_file in sorted(dir_alumno.glob("**/*.c")):
            codigo = c_file.read_text(encoding="utf-8", errors="replace")
            trozos.append(stripper.limpiar(codigo))
        resultados[dir_alumno.name] = "\n\n".join(trozos)
    return resultados
