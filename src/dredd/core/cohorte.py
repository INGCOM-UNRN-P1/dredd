"""Hallazgos en la taxonomía común, devolución con enlaces al apunte y errores por cohorte.

- Junto a los informes de cada revisión (`rNi/`) queda `hallazgos.json`: lo que encontraron ripley
  y sus satélites en la forma común del ecosistema (`yutani.hallazgos`: id estable, categoría y
  enlace a la página del apunte o a la regla exacta).
- `para_repasar.md` entra en el informe del estudiante: por cada tema donde tuvo errores, el enlace
  a esa sección del apunte y a las reglas que no cumplió (revisión 07, devolución con enlaces).
- `dredd cluster-errors` agrupa los `hallazgos.json` de un curso: qué errores comete más gente y en
  qué temas (QoL #331), lo que hay que reforzar en clase.
"""

from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List

from yutani.hallazgos import CATEGORIAS, enlace_apunte, hallazgo

ARCHIVO = "hallazgos.json"
_REGLA = re.compile(r"^0x[0-9A-Fa-f]{4}h$")
_POR_FAMILIA = {"0": "estilo", "1": "control", "2": "funciones", "3": "memoria", "4": "archivos",
                "5": "seguridad", "6": "compilacion", "7": "funciones", "8": "pruebas"}


def _categoria(codigo: str, herramienta: str) -> str:
    if _REGLA.match(codigo):
        return _POR_FAMILIA.get(codigo[2], "estilo")
    por_herramienta = {"kaneda": "seguridad", "tetsuo": "memoria", "hal": "punteros", "valgrind": "memoria",
                       "daedalus": "compilacion", "compiler": "compilacion", "corbel": "documentacion",
                       "motoko": "tad", "zhora": "compilacion", "brett": "estructuras", "wierzbowski": "compilacion"}
    return por_herramienta.get(herramienta, "estilo")


def a_hallazgos(analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Los hallazgos estáticos del análisis de ripley en la forma común (los repetidos, una vez)."""
    resultado, vistos = [], set()
    for f in list(analysis.get("ast_findings", [])) + list(analysis.get("style_findings", [])):
        codigo = str(f.get("rule_code") or f.get("codigo") or "").strip()
        if not codigo:
            continue
        herramienta = str(f.get("source_plugin") or "ripley").strip().lower() or "ripley"
        herramienta = herramienta.replace(":", "_")
        clave = (herramienta, codigo, f.get("file"), f.get("line"))
        if clave in vistos:
            continue
        vistos.add(clave)
        try:
            resultado.append(hallazgo(herramienta, codigo, _categoria(codigo, herramienta),
                                      str(f.get("severity") or "advertencia"), str(f.get("message") or ""),
                                      archivo=f.get("file"), linea=f.get("line") or None))
        except ValueError:
            resultado.append(hallazgo(herramienta, codigo, _categoria(codigo, herramienta), "advertencia",
                                      str(f.get("message") or ""), archivo=f.get("file"), linea=f.get("line") or None))
    return resultado


def para_repasar(hallazgos: List[Dict[str, Any]]) -> str:
    """La sección del informe con los enlaces al apunte, por tema."""
    if not hallazgos:
        return ""
    por_categoria: Dict[str, Counter] = defaultdict(Counter)
    for h in hallazgos:
        por_categoria[h["categoria"]][h["codigo"]] += 1
    lineas = ["## Para repasar\n", "Los temas del apunte relacionados con lo que se encontró en esta entrega:\n"]
    for categoria, codigos in sorted(por_categoria.items(), key=lambda kv: -sum(kv[1].values())):
        descripcion = CATEGORIAS[categoria][0]
        enlace = enlace_apunte(categoria)
        tema = f"[{descripcion}]({enlace})" if enlace else descripcion
        reglas = [f"[{c}]({enlace_apunte(categoria, c)})" for c, _ in codigos.most_common(5) if _REGLA.match(c)]
        lineas.append(f"- {tema}" + (f" — reglas: {', '.join(reglas)}" if reglas else ""))
    return "\n".join(lineas) + "\n"


def escribir(rni_dir: Path, analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
    hallazgos = a_hallazgos(analysis)
    rni_dir.mkdir(parents=True, exist_ok=True)
    (rni_dir / ARCHIVO).write_text(json.dumps({"schema_version": "1.0.0", "hallazgos": hallazgos},
                                              indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    texto = para_repasar(hallazgos)
    if texto:
        (rni_dir / "para_repasar.md").write_text(texto, encoding="utf-8")
    return hallazgos


def agrupar_cohorte(raiz: Path) -> Dict[str, Any]:
    """Errores por cohorte: cuántos estudiantes distintos tuvieron cada error y cada tema. De cada
    estudiante cuenta su última revisión (el `rNi` más alto)."""
    ultima: Dict[Path, Path] = {}
    for archivo in Path(raiz).rglob(ARCHIVO):
        alumno = archivo.parent.parent
        actual = ultima.get(alumno)
        if actual is None or _numero(archivo.parent.name) > _numero(actual.parent.name):
            ultima[alumno] = archivo
    por_id: Dict[str, set] = defaultdict(set)
    por_categoria: Dict[str, set] = defaultdict(set)
    info: Dict[str, Dict[str, Any]] = {}
    for alumno, archivo in ultima.items():
        try:
            hallazgos = json.loads(archivo.read_text(encoding="utf-8")).get("hallazgos", [])
        except (OSError, ValueError):
            continue
        for h in hallazgos:
            por_id[h["id"]].add(alumno)
            por_categoria[h["categoria"]].add(alumno)
            info.setdefault(h["id"], {"categoria": h["categoria"], "enlace": h.get("enlace"), "ejemplo": h.get("mensaje", "")})
    total = len(ultima)
    errores = [{"id": i, "alumnos": len(a), "porcentaje": round(100 * len(a) / total, 1) if total else 0.0, **info[i]}
               for i, a in por_id.items()]
    temas = [{"categoria": c, "descripcion": CATEGORIAS[c][0], "alumnos": len(a),
              "porcentaje": round(100 * len(a) / total, 1) if total else 0.0, "enlace": enlace_apunte(c)}
             for c, a in por_categoria.items()]
    return {"schema_version": "1.0.0", "estudiantes": total,
            "errores": sorted(errores, key=lambda e: (-e["alumnos"], e["id"])),
            "temas": sorted(temas, key=lambda t: (-t["alumnos"], t["categoria"]))}


def _numero(nombre_rni: str) -> int:
    m = re.search(r"\d+", nombre_rni)
    return int(m.group(0)) if m else 0
