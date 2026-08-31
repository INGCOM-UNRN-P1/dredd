"""Comparador de versiones sucesivas de la misma entrega (QoL 3.15 / dredd diff-submission)."""

from __future__ import annotations

from dataclasses import dataclass, field
import difflib
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Set, Tuple


@dataclass
class DiffArchivo:
    nombre: str
    estado: str  # "MODIFICADO", "NUEVO", "ELIMINADO", "IDENTICO"
    lineas_agregadas: int
    lineas_eliminadas: int
    diff_unified: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "nombre": self.nombre,
            "estado": self.estado,
            "lineas_agregadas": self.lineas_agregadas,
            "lineas_eliminadas": self.lineas_eliminadas,
            "diff_unified": self.diff_unified,
        }


@dataclass
class DiffEntrega:
    origen_r1: Path
    origen_r2: Path
    revision_1: str
    revision_2: str
    archivos: List[DiffArchivo]
    total_agregadas: int
    total_eliminadas: int
    archivos_modificados: int
    archivos_nuevos: int
    archivos_eliminados: int
    funciones_alteradas: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "origen_r1": str(self.origen_r1),
            "origen_r2": str(self.origen_r2),
            "revision_1": self.revision_1,
            "revision_2": self.revision_2,
            "total_agregadas": self.total_agregadas,
            "total_eliminadas": self.total_eliminadas,
            "archivos_modificados": self.archivos_modificados,
            "archivos_nuevos": self.archivos_nuevos,
            "archivos_eliminados": self.archivos_eliminados,
            "funciones_alteradas": self.funciones_alteradas,
            "archivos": [a.to_dict() for a in self.archivos],
        }


def _extraer_funciones_c(contenido: str) -> Set[str]:
    """Extrae nombres de funciones declaradas o definidas en un archivo C."""
    patron = re.compile(r"\b(?:[a-zA-Z_]\w*\s+)+([a-zA-Z_]\w*)\s*\([^;{}]*\)\s*\{", re.MULTILINE)
    return set(patron.findall(contenido))


def resolver_carpetas_revision(
    objetivo: str,
    rev1_name: Optional[str] = None,
    rev2_name: Optional[str] = None,
    base_dir: Optional[Path] = None,
) -> Tuple[Path, Path, str, str]:
    """
    Resuelve los dos directorios a comparar a partir de argumentos CLI flexibles:
    1. Dos rutas de carpetas directas.
    2. Un directorio de alumno que contiene subcarpetas r1/ y r2/ (o R1/ y R2/).
    3. Nombre de alumno y nombres explícitos de revisiones.
    """
    p_obj = Path(objetivo).resolve()

    # Caso 1: Objetivo es una ruta que existe y rev1_name es una segunda ruta que existe
    if p_obj.exists() and rev1_name:
        p_rev2 = Path(rev1_name).resolve()
        if p_rev2.exists():
            return p_obj, p_rev2, p_obj.name, p_rev2.name

    # Caso 2: p_obj es una carpeta de alumno y tiene subcarpetas r1/r2 o se pasan rev1_name/rev2_name
    if p_obj.is_dir():
        r1_tag = rev1_name or "r1"
        r2_tag = rev2_name or "r2"

        # Buscar r1, R1, entrega_1, etc.
        cand_r1 = [p_obj / r1_tag, p_obj / r1_tag.upper(), p_obj / f"entrega_{r1_tag}"]
        cand_r2 = [p_obj / r2_tag, p_obj / r2_tag.upper(), p_obj / f"entrega_{r2_tag}"]

        dir_r1 = next((c for c in cand_r1 if c.is_dir()), None)
        dir_r2 = next((c for c in cand_r2 if c.is_dir()), None)

        if dir_r1 and dir_r2:
            return dir_r1, dir_r2, r1_tag, r2_tag

    # Caso 3: Buscar en base_dir (por ejemplo submissions/ o entregas/)
    if base_dir:
        b = Path(base_dir).resolve()
        alumno_dir = b / objetivo
        if alumno_dir.is_dir():
            return resolver_carpetas_revision(str(alumno_dir), rev1_name, rev2_name)

    # Fallback si se pasaron rutas directas aunque p_obj no existiese
    p_r1 = Path(objetivo).resolve()
    p_r2 = Path(rev1_name or "").resolve()
    return p_r1, p_r2, p_r1.name, p_r2.name


def comparar_revisiones_entrega(
    dir_r1: Path,
    dir_r2: Path,
    label_r1: str = "r1",
    label_r2: str = "r2",
    extensiones: Tuple[str, ...] = (".c", ".h", ".cpp", ".hpp", "Makefile", ".txt", ".md"),
) -> DiffEntrega:
    """Compara todos los archivos fuente entre dos revisiones de una entrega."""
    r1 = Path(dir_r1).resolve()
    r2 = Path(dir_r2).resolve()

    if not r1.exists():
        raise FileNotFoundError(f"No existe el directorio de origen R1: {r1}")
    if not r2.exists():
        raise FileNotFoundError(f"No existe el directorio de origen R2: {r2}")

    # Recolectar archivos relativos en ambos directorios
    def _recolectar(d: Path) -> Dict[str, Path]:
        res = {}
        if d.is_file():
            res[d.name] = d
            return res
        for item in d.rglob("*"):
            if item.is_file() and not any(part.startswith(".") for part in item.parts):
                if item.name.startswith("reporte_") or item.name.startswith("informe_"):
                    continue
                if item.suffix in extensiones or item.name in extensiones:
                    rel = str(item.relative_to(d))
                    res[rel] = item
        return res

    archivos_r1 = _recolectar(r1)
    archivos_r2 = _recolectar(r2)

    todos_nombres = sorted(set(archivos_r1.keys()) | set(archivos_r2.keys()))

    diffs: List[DiffArchivo] = []
    tot_add = 0
    tot_del = 0
    modificados = 0
    nuevos = 0
    eliminados = 0
    funciones_alteradas_set: Set[str] = set()

    for nombre in todos_nombres:
        p1 = archivos_r1.get(nombre)
        p2 = archivos_r2.get(nombre)

        if p1 and p2:
            txt1 = p1.read_text(encoding="utf-8", errors="replace")
            txt2 = p2.read_text(encoding="utf-8", errors="replace")

            if txt1 == txt2:
                diffs.append(DiffArchivo(
                    nombre=nombre,
                    estado="IDENTICO",
                    lineas_agregadas=0,
                    lineas_eliminadas=0,
                    diff_unified="",
                ))
            else:
                lines1 = txt1.splitlines(keepends=True)
                lines2 = txt2.splitlines(keepends=True)
                u_diff = list(difflib.unified_diff(
                    lines1, lines2,
                    fromfile=f"{label_r1}/{nombre}",
                    tofile=f"{label_r2}/{nombre}",
                ))
                add = sum(1 for l in u_diff if l.startswith("+") and not l.startswith("+++"))
                rem = sum(1 for l in u_diff if l.startswith("-") and not l.startswith("---"))

                # Extraer funciones modificadas si es C
                if nombre.endswith((".c", ".h")):
                    fn1 = _extraer_funciones_c(txt1)
                    fn2 = _extraer_funciones_c(txt2)
                    funciones_alteradas_set.update(fn1 ^ fn2)

                tot_add += add
                tot_del += rem
                modificados += 1

                diffs.append(DiffArchivo(
                    nombre=nombre,
                    estado="MODIFICADO",
                    lineas_agregadas=add,
                    lineas_eliminadas=rem,
                    diff_unified="".join(u_diff),
                ))

        elif p2 and not p1:
            txt2 = p2.read_text(encoding="utf-8", errors="replace")
            lines2 = txt2.splitlines(keepends=True)
            u_diff = list(difflib.unified_diff(
                [], lines2,
                fromfile=f"/dev/null",
                tofile=f"{label_r2}/{nombre}",
            ))
            add = len(lines2)
            tot_add += add
            nuevos += 1
            if nombre.endswith((".c", ".h")):
                funciones_alteradas_set.update(_extraer_funciones_c(txt2))

            diffs.append(DiffArchivo(
                nombre=nombre,
                estado="NUEVO",
                lineas_agregadas=add,
                lineas_eliminadas=0,
                diff_unified="".join(u_diff),
            ))

        elif p1 and not p2:
            txt1 = p1.read_text(encoding="utf-8", errors="replace")
            lines1 = txt1.splitlines(keepends=True)
            u_diff = list(difflib.unified_diff(
                lines1, [],
                fromfile=f"{label_r1}/{nombre}",
                tofile=f"/dev/null",
            ))
            rem = len(lines1)
            tot_del += rem
            eliminados += 1
            if nombre.endswith((".c", ".h")):
                funciones_alteradas_set.update(_extraer_funciones_c(txt1))

            diffs.append(DiffArchivo(
                nombre=nombre,
                estado="ELIMINADO",
                lineas_agregadas=0,
                lineas_eliminadas=rem,
                diff_unified="".join(u_diff),
            ))

    return DiffEntrega(
        origen_r1=r1,
        origen_r2=r2,
        revision_1=label_r1,
        revision_2=label_r2,
        archivos=diffs,
        total_agregadas=tot_add,
        total_eliminadas=tot_del,
        archivos_modificados=modificados,
        archivos_nuevos=nuevos,
        archivos_eliminados=eliminados,
        funciones_alteradas=sorted(funciones_alteradas_set),
    )


def generar_markdown_diff_submission(
    diff: DiffEntrega,
    titulo: Optional[str] = None,
) -> str:
    """Genera un reporte Markdown estructurado con el diff de reentrega para el docente."""
    nombre_tit = titulo or f"Comparativa de Reentrega: `{diff.revision_1}` vs `{diff.revision_2}`"
    lines = [
        f"# {nombre_tit}\n",
        f"- **Origen {diff.revision_1}:** `{diff.origen_r1}`",
        f"- **Origen {diff.revision_2}:** `{diff.origen_r2}`",
        f"- **Archivos modificados:** {diff.archivos_modificados}",
        f"- **Archivos nuevos:** {diff.archivos_nuevos}",
        f"- **Archivos eliminados:** {diff.archivos_eliminados}",
        f"- **Líneas agregadas:** `+{diff.total_agregadas}`",
        f"- **Líneas eliminadas:** `-{diff.total_eliminadas}`\n",
    ]

    if diff.funciones_alteradas:
        lines.append("### Funciones C Añadidas, Modificadas o Eliminadas\n")
        for fn in diff.funciones_alteradas:
            lines.append(f"- `{fn}()`")
        lines.append("")

    lines.append("## Detalle de Archivos\n")
    lines.append("| Archivo | Estado | Agregadas | Eliminadas |")
    lines.append("| :--- | :---: | :---: | :---: |")
    for a in diff.archivos:
        lines.append(f"| `{a.nombre}` | `{a.estado}` | `+{a.lineas_agregadas}` | `-{a.lineas_eliminadas}` |")
    lines.append("")

    # Bloques de diff unificado
    hay_cambios = any(a.diff_unified for a in diff.archivos)
    if hay_cambios:
        lines.append("## Cambios de Código (Unified Diff)\n")
        for a in diff.archivos:
            if a.diff_unified:
                lines.append(f"### `{a.nombre}` ({a.estado})\n")
                lines.append(f"```diff\n{a.diff_unified}\n```\n")
    else:
        lines.append("> [!NOTE]\n> No se detectaron diferencias en el código fuente entre ambas versiones.\n")

    return "\n".join(lines)
