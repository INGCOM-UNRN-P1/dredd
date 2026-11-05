"""Paquete para el calificador de Moodle desde las notas de deckard (Ola 46).

`deckard exercise rubric --eval-results` deja `calificaciones.csv` y `devoluciones/<alumno>.md`.
`dredd moodle paquete` los convierte en lo que importa una tarea de Moodle:

- `planilla_moodle.csv`: la **hoja de calificaciones que el docente descargó de esa tarea**, con la
  nota y el comentario completos. Se parte de ella porque Moodle busca los encabezados y el prefijo
  del identificador (`Participante 12`) en el idioma de la cuenta, y el número de participante es
  interno de la tarea: fabricarlos no funciona, y una entrega de GitHub Classroom ni siquiera lo tiene.
- `devoluciones_moodle.zip`: una devolución en HTML por estudiante, como archivo de retroalimentación.

Lo que no sale de un dato seguro no se adivina, porque terminaría en el libro de calificaciones:

- Cada estudiante se vincula por el `--mapa`, por el número de participante de una ingesta de Moodle
  (`perez-juan_123`) o por el nombre exacto. Sin coincidencia exacta, queda afuera y se informa.
- Una nota provisoria deja la fila intacta. No alcanza con vaciar la nota: Moodle importa el
  comentario de una fila sin nota.
- La nota de deckard es sobre 10 y se reescala al máximo de la tarea; Moodle no avisa si es otro.
"""

from __future__ import annotations

import csv
import html
import re
import tempfile
import unicodedata
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

ESCALA_DE_DECKARD = 10.0
_PARTICIPANTE_DE_INGESTA = re.compile(r"_(\d+)$")
_PARTICIPANTE = re.compile(r"(\d+)\s*$")


class PaqueteError(ValueError):
    """La planilla, las notas o el mapa no permiten armar el paquete."""


@dataclass
class Columnas:
    identificador: str
    nombre: str
    nota: str
    comentarios: str
    maximo: Optional[str]
    correo: Optional[str]


@dataclass
class ResultadoPaquete:
    planilla: Path
    zip: Optional[Path]
    importadas: List[str] = field(default_factory=list)
    provisorias: List[str] = field(default_factory=list)
    sin_vincular: List[str] = field(default_factory=list)
    sin_devolucion: List[str] = field(default_factory=list)
    filas_sin_nota: int = 0


def _clave(texto: str) -> str:
    """Sin mayúsculas, acentos ni separadores: `Pérez, Juan` y `perez-juan` no son iguales, pero
    `Pérez Juan` y `perez-juan` sí."""
    plano = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode().lower()
    return " ".join(re.sub(r"[^a-z0-9@.]+", " ", plano).split())


def _una(encabezados: Sequence[str], condicion, que: str, pedida: Optional[str]) -> str:
    if pedida:
        if pedida not in encabezados:
            raise PaqueteError(f"La planilla no tiene la columna «{pedida}». Tiene: {', '.join(encabezados)}.")
        return pedida
    halladas = [e for e in encabezados if condicion(_clave(e))]
    if len(halladas) != 1:
        problema = "varias columnas posibles" if halladas else "ninguna columna"
        raise PaqueteError(f"No se pudo elegir la columna de {que} ({problema}). Tiene: {', '.join(encabezados)}.")
    return halladas[0]


def detectar_columnas(encabezados: Sequence[str], columna_nota: Optional[str] = None,
                      columna_comentarios: Optional[str] = None) -> Columnas:
    def opcional(condicion) -> Optional[str]:
        halladas = [e for e in encabezados if condicion(_clave(e))]
        return halladas[0] if len(halladas) == 1 else None

    try:
        comentarios = _una(encabezados, lambda c: "comentario" in c or c == "feedback comments", "comentarios",
                           columna_comentarios)
    except PaqueteError as e:
        raise PaqueteError(f"{e} Activá «Comentarios de retroalimentación» en la tarea y volvé a descargar la "
                           "planilla.") from None
    return Columnas(
        identificador=_una(encabezados, lambda c: c in ("identificador", "identifier"), "identificador", None),
        nombre=_una(encabezados, lambda c: c in ("nombre completo", "full name"), "nombre", None),
        nota=_una(encabezados, lambda c: c in ("calificacion", "grade", "nota"), "calificación", columna_nota),
        comentarios=comentarios,
        maximo=opcional(lambda c: "maxim" in c),
        correo=opcional(lambda c: "correo" in c or "email" in c),
    )


def leer_planilla(ruta: Path) -> Tuple[List[str], List[Dict[str, str]], str]:
    """(encabezados, filas, separador). Moodle la baja con comas; se respeta si alguien la guardó con `;`."""
    texto = ruta.read_text(encoding="utf-8-sig")
    primera = texto.splitlines()[0] if texto.strip() else ""
    separador = ";" if primera.count(";") > primera.count(",") else ","
    lector = csv.DictReader(texto.splitlines(keepends=True), delimiter=separador)
    filas = list(lector)
    if not lector.fieldnames or not filas:
        raise PaqueteError(f"{ruta} no tiene estudiantes: descargala de la tarea con «Descargar hoja de calificaciones».")
    return list(lector.fieldnames), filas, separador


def leer_mapa(ruta: Optional[Path]) -> Dict[str, str]:
    """{alumno: identificador, correo o nombre en Moodle}, de un CSV de dos columnas."""
    if ruta is None:
        return {}
    mapa: Dict[str, str] = {}
    with open(ruta, newline="", encoding="utf-8-sig") as f:
        for numero, fila in enumerate(csv.reader(f), 1):
            if not fila or (numero == 1 and fila[0].strip().lower() == "alumno"):
                continue
            if len(fila) < 2 or not fila[1].strip():
                raise PaqueteError(f"{ruta}:{numero}: hacen falta dos columnas, alumno y su dato en Moodle.")
            mapa[fila[0].strip()] = fila[1].strip()
    return mapa


def _participante(fila: Dict[str, str], columnas: Columnas) -> Optional[str]:
    m = _PARTICIPANTE.search(fila.get(columnas.identificador) or "")
    return m.group(1) if m else None


def _indices(filas: List[Dict[str, str]], columnas: Columnas) -> Dict[str, int]:
    """Clave → fila. Una clave repetida (dos personas con el mismo nombre) no sirve para vincular."""
    indice: Dict[str, int] = {}
    repetidas = set()
    for i, fila in enumerate(filas):
        claves = {_participante(fila, columnas), _clave(fila.get(columnas.nombre) or "")}
        if columnas.correo:
            claves.add(_clave(fila.get(columnas.correo) or ""))
        for clave in claves - {None, ""}:
            if clave in indice:
                repetidas.add(clave)
            indice[str(clave)] = i
    return {k: v for k, v in indice.items() if k not in repetidas}


def vincular(alumno: str, mapa: Dict[str, str], indice: Dict[str, int]) -> Optional[int]:
    if alumno in mapa:
        dato = mapa[alumno]
        m = _PARTICIPANTE.search(dato)
        return indice.get(_clave(dato), indice.get(m.group(1)) if m else None)
    ingesta = _PARTICIPANTE_DE_INGESTA.search(alumno)
    if ingesta and ingesta.group(1) in indice:
        return indice[ingesta.group(1)]
    return indice.get(_clave(alumno))


def _numero(texto: str) -> Optional[float]:
    try:
        return float((texto or "").strip().replace(",", "."))
    except ValueError:
        return None


def _maximo_de(fila: Dict[str, str], columnas: Columnas, pedido: Optional[float]) -> float:
    if pedido is not None:
        return pedido
    maximo = _numero(fila.get(columnas.maximo) or "") if columnas.maximo else None
    if maximo is None or maximo <= 0:
        raise PaqueteError("No se sabe la calificación máxima de la tarea (¿usa una escala?): indicala con --maximo. "
                           "Si no, la nota sobre 10 quedaría mal sin que Moodle avise.")
    return maximo


def _html_de_devolucion(markdown: Path, destino: Path) -> Path:
    from dredd.core.report_export import export_report

    return export_report(markdown, fmt="html", out_path=destino, title=f"Devolución de {markdown.stem}")


def _nombre_en_zip(nombre: str, participante: str) -> str:
    # Moodle ignora el nombre y toma el número del segundo campo: el nombre no puede tener «_».
    limpio = re.sub(r"[_/\\]+", " ", nombre).strip() or "estudiante"
    return f"{limpio}_{participante}_assignfeedback_file/devolucion.html"


def armar_paquete(planilla: Path, notas: Path, salida: Path, devoluciones: Optional[Path] = None,
                  mapa: Optional[Path] = None, incluir_provisorias: bool = False, maximo: Optional[float] = None,
                  columna_nota: Optional[str] = None, columna_comentarios: Optional[str] = None) -> ResultadoPaquete:
    encabezados, filas, separador = leer_planilla(planilla)
    columnas = detectar_columnas(encabezados, columna_nota, columna_comentarios)
    indice = _indices(filas, columnas)
    vinculos = leer_mapa(mapa)
    devoluciones = devoluciones if devoluciones is not None else notas.parent / "devoluciones"

    with open(notas, newline="", encoding="utf-8-sig") as f:
        calificaciones = list(csv.DictReader(f))
    if not calificaciones or "Usuario" not in calificaciones[0] or "Calificación" not in calificaciones[0]:
        raise PaqueteError(f"{notas} no es un calificaciones.csv de deckard (columnas Usuario y Calificación).")

    salida.mkdir(parents=True, exist_ok=True)
    res = ResultadoPaquete(salida / "planilla_moodle.csv", None)
    para_zip: List[Tuple[str, Path]] = []
    usadas: Dict[int, str] = {}
    for c in calificaciones:
        alumno = c["Usuario"]
        i = vincular(alumno, vinculos, indice)
        if i is None:
            res.sin_vincular.append(alumno)
            continue
        if i in usadas:
            raise PaqueteError(f"{alumno} y {usadas[i]} van a la misma fila de la planilla: revisá el mapa.")
        usadas[i] = alumno
        if (c.get("Provisoria") or "").strip().lower() in ("sí", "si") and not incluir_provisorias:
            res.provisorias.append(alumno)
            continue
        nota = _numero(c["Calificación"])
        if nota is None:
            raise PaqueteError(f"{alumno}: la calificación «{c['Calificación']}» no es un número.")
        fila = filas[i]
        tope = _maximo_de(fila, columnas, maximo)
        fila[columnas.nota] = f"{nota * tope / ESCALA_DE_DECKARD:.2f}"
        fila[columnas.comentarios] = html.escape(c.get("Comentarios de retroalimentación") or "", quote=False)
        res.importadas.append(alumno)
        markdown = devoluciones / f"{alumno}.md"
        participante = _participante(fila, columnas)
        if markdown.is_file() and participante:
            para_zip.append((_nombre_en_zip(fila.get(columnas.nombre) or alumno, participante), markdown))
        else:
            res.sin_devolucion.append(alumno)
    res.filas_sin_nota = len(filas) - len(res.importadas)

    with open(res.planilla, "w", newline="", encoding="utf-8") as f:
        escritor = csv.DictWriter(f, fieldnames=encabezados, delimiter=separador, lineterminator="\n")
        escritor.writeheader()
        escritor.writerows(filas)
    if para_zip:
        res.zip = salida / "devoluciones_moodle.zip"
        with tempfile.TemporaryDirectory(prefix="dredd-moodle-") as tmp, \
                zipfile.ZipFile(res.zip, "w", zipfile.ZIP_DEFLATED) as zf:
            for nombre, markdown in para_zip:
                zf.write(_html_de_devolucion(markdown, Path(tmp) / "devolucion.html"), arcname=nombre)
    return res
