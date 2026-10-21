"""Similitud estructural en la cohorte (Ola 8): `dredd cluster-errors --similitud`.

Agrupa las entregas que son el mismo programa salvo nombres, comentarios, formato u orden de las
funciones, para que el docente mire esos grupos a mano. Es la misma medida que `weyl similarity`
(dos archivos), llevada a todo el curso:

- tree-sitter separa cada entrega en sus definiciones de primer nivel (funciones, structs,
  globales); los comentarios, los `#include` y los prototipos no cuentan.
- Cada definición se normaliza por separado con la alfa-equivalencia de weyl (los identificadores
  pasan a `_v0`, `_v1`… en orden de aparición) y se ordenan: renombrar variables o funciones y
  reordenar las funciones no cambia la forma canónica. Sin weyl instalado se usan los tokens del
  detector de plagio de dredd (identificadores y números genéricos), y el informe lo dice.
- La similitud de dos entregas es la proporción de coincidencia (SequenceMatcher) de sus formas
  canónicas; las que superan el umbral quedan en el mismo grupo (componentes conexas).

El resultado tiene nombres de estudiantes y porcentajes, nunca código: se puede compartir con otros
docentes sin exponer las entregas.
"""

from __future__ import annotations

import difflib
import re
from itertools import combinations
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional, Tuple

_INTERMEDIO = re.compile(r"^(r\d+i|i_.+)$")
_REVISION = re.compile(r"^r(\d+)i$")
_IGNORADOS = {"comment", "preproc_include"}


def motor() -> Tuple[str, Callable[[str], str]]:
    """El normalizador de identificadores: el de weyl si está instalado, si no el de dredd."""
    try:
        from weyl.core.alpha_equiv import normalizar_alpha_equivalencia
        from weyl.core.masking import eliminar_comentarios
    except ImportError:
        from dredd.core.plagiarism import tokenize_c_code

        return "dredd", lambda codigo: " ".join(t for t, _ in tokenize_c_code(codigo))
    return "weyl", lambda codigo: normalizar_alpha_equivalencia(eliminar_comentarios(codigo))


def fuentes_de_revision(rni_dir: Path) -> List[Path]:
    """Los `.c` de la revisión que evaluó `rni_dir`: `rN/` para `rNi/`, el repositorio para `i_<hash>/`."""
    alumno = rni_dir.parent
    m = _REVISION.match(rni_dir.name)
    candidatos: List[Path] = []
    if m:
        candidatos = [alumno / f"r{m.group(1)}", alumno / f"r{m.group(1)}_f"]
    candidatos.append(alumno / "repo")
    raiz = next((c for c in candidatos if c.is_dir()), alumno)
    return sorted(
        p for p in raiz.rglob("*.c")
        if not any(_INTERMEDIO.match(parte) or parte.startswith(".")
                   for parte in p.relative_to(raiz).parts[:-1])
    )


def forma_canonica(codigo: str, normalizar: Callable[[str], str]) -> str:
    """Las definiciones de primer nivel normalizadas una por una y ordenadas."""
    from dredd.core.ast_checker import get_c_parser

    arbol = get_c_parser().parse(codigo.encode("utf-8", errors="replace"))
    trozos = [normalizar(n.text.decode("utf-8", errors="replace"))
              for n in arbol.root_node.children if n.type not in _IGNORADOS and n.text and not _es_prototipo(n)]
    return "\n".join(sorted(t for t in trozos if t))


def _es_prototipo(nodo: Any) -> bool:
    """`int f(int x);`: declarar o no los prototipos no cambia el programa."""
    if nodo.type != "declaration":
        return False
    pendientes = list(nodo.children)
    while pendientes:
        hijo = pendientes.pop()
        if hijo.type == "function_declarator":
            return True
        if hijo.type in ("pointer_declarator", "parenthesized_declarator"):
            pendientes.extend(hijo.children)
    return False


def similitud(a: str, b: str) -> float:
    return round(difflib.SequenceMatcher(None, a, b, autojunk=False).ratio() * 100.0, 1)


def _supera(a: str, b: str, umbral: float) -> Optional[float]:
    comparador = difflib.SequenceMatcher(None, a, b, autojunk=False)
    # Las cotas rápidas descartan la mayoría de los pares sin el cálculo cuadrático.
    if comparador.real_quick_ratio() * 100.0 < umbral or comparador.quick_ratio() * 100.0 < umbral:
        return None
    valor = round(comparador.ratio() * 100.0, 1)
    return valor if valor >= umbral else None


def agrupar(entregas: Mapping[str, Iterable[Path]], umbral: float = 90.0,
            plantilla: Optional[Path] = None) -> Dict[str, Any]:
    """Grupos de entregas con similitud ≥ `umbral` (porcentaje) y su matriz de similitud."""
    nombre_motor, normalizar = motor()
    stripper = None
    if plantilla is not None:
        from dredd.core.boiler_strip import BoilerStripper

        stripper = BoilerStripper(ventanas_minimas=2)
        stripper.cargar_plantilla(plantilla)

    formas: Dict[str, str] = {}
    sin_codigo: List[str] = []
    for alumno, archivos in sorted(entregas.items()):
        codigo = "\n".join(p.read_text(encoding="utf-8", errors="replace") for p in archivos)
        if stripper is not None:
            codigo = stripper.limpiar(codigo)
        forma = forma_canonica(codigo, normalizar) if codigo.strip() else ""
        if forma:
            formas[alumno] = forma
        else:
            sin_codigo.append(alumno)

    padre = {a: a for a in formas}

    def raiz(a: str) -> str:
        while padre[a] != a:
            padre[a] = padre[padre[a]]
            a = padre[a]
        return a

    pares = []
    for a, b in combinations(sorted(formas), 2):
        valor = _supera(formas[a], formas[b], umbral)
        if valor is not None:
            pares.append({"a": a, "b": b, "similitud_pct": valor})
            padre[raiz(a)] = raiz(b)

    miembros: Dict[str, List[str]] = {}
    for a in formas:
        miembros.setdefault(raiz(a), []).append(a)
    grupos: List[Dict[str, Any]] = []
    for alumnos in miembros.values():
        if len(alumnos) < 2:
            continue
        alumnos.sort()
        matriz = {a: {b: (100.0 if a == b else similitud(formas[a], formas[b])) for b in alumnos} for a in alumnos}
        valores = [matriz[a][b] for a, b in combinations(alumnos, 2)]
        grupos.append({"alumnos": alumnos, "similitud_min": min(valores), "similitud_max": max(valores),
                       "matriz": matriz})
    grupos.sort(key=lambda g: (-len(g["alumnos"]), -g["similitud_max"], g["alumnos"]))
    return {
        "motor": nombre_motor,
        "umbral_pct": umbral,
        "estudiantes": len(formas) + len(sin_codigo),
        "sin_codigo": sin_codigo,
        "grupos": grupos,
        "pares": sorted(pares, key=lambda p: (-p["similitud_pct"], p["a"], p["b"])),
    }


def informe_markdown(datos: Dict[str, Any]) -> str:
    """El informe docente: los grupos y su matriz de similitud, sin código de las entregas."""
    lineas = [
        "# Similitud estructural de la cohorte\n",
        f"{datos['estudiantes']} entregas comparadas; umbral {datos['umbral_pct']:g} %; normalización "
        f"{'de weyl (alfa-equivalencia)' if datos['motor'] == 'weyl' else 'de dredd (weyl no está instalado)'}. "
        "Cada grupo reúne entregas que, salvo nombres, comentarios, formato y orden de las funciones, "
        "son el mismo programa: revisalas a mano antes de sacar conclusiones (una consigna muy guiada "
        "también produce soluciones parecidas).\n",
    ]
    if not datos["grupos"]:
        lineas.append("No hay entregas por encima del umbral.\n")
    for i, grupo in enumerate(datos["grupos"], 1):
        alumnos = grupo["alumnos"]
        lineas.append(f"## Grupo {i}: {len(alumnos)} entregas ({grupo['similitud_min']:g}–{grupo['similitud_max']:g} %)\n")
        lineas.append("| | " + " | ".join(alumnos) + " |")
        lineas.append("| :--- |" + " ---: |" * len(alumnos))
        for a in alumnos:
            lineas.append(f"| **{a}** | " + " | ".join("—" if a == b else f"{grupo['matriz'][a][b]:g}" for b in alumnos) + " |")
        lineas.append("")
    if datos["sin_codigo"]:
        lineas.append(f"Sin código C para comparar: {', '.join(datos['sin_codigo'])}.\n")
    return "\n".join(lineas)
