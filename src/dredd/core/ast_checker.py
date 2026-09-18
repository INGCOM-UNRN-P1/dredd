"""Linter nativo de reglas de cátedra P1 y verificación estática usando Tree-Sitter AST en Dredd.

Este módulo actúa como motor nativo y linter fallback autónomo cuando la herramienta
especializada de cátedra (`gaff` o `ripley`) no se encuentra instalada en el entorno o cuando
se requiere verificación rápida e independiente sin dependencias satélite adicionales.
Implementa un subconjunto canónico de reglas de estilo y arquitectura de Cátedra P1 (0xXXXXh).
"""

from __future__ import annotations

import bisect
from collections import defaultdict
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Tuple

import tree_sitter_c as tsc
from tree_sitter import Language, Parser, Node, Query

try:
    from tree_sitter import QueryCursor
except ImportError:
    QueryCursor = None


def _get_line_starts(content_bytes: bytes) -> List[int]:
    """Calcula los offsets de inicio de cada línea para búsqueda binaria rápida."""
    starts = [0]
    for idx, b in enumerate(content_bytes):
        if b == ord('\n'):
            starts.append(idx + 1)
    return starts


def _byte_to_line(starts: List[int], byte_offset: int) -> int:
    """Traduce un offset de byte a un número de línea 1-indexed mediante búsqueda binaria."""
    return bisect.bisect_right(starts, byte_offset)

_C_LANGUAGE: Optional[Language] = None
_PARSER: Optional[Parser] = None
_VAR_QUERY: Optional[Query] = None


def get_c_language() -> Language:
    global _C_LANGUAGE
    if _C_LANGUAGE is None:
        _C_LANGUAGE = Language(tsc.language())
    return _C_LANGUAGE


def get_c_parser() -> Parser:
    global _PARSER
    if _PARSER is None:
        _PARSER = Parser(get_c_language())
    return _PARSER


def get_var_query() -> Query:
    global _VAR_QUERY
    if _VAR_QUERY is None:
        _VAR_QUERY = Query(
            get_c_language(),
            """
            (parameter_declaration
              declarator: [
                (identifier) @param
                (pointer_declarator (identifier) @param)
                (pointer_declarator (pointer_declarator (identifier) @param))
                (pointer_declarator (pointer_declarator (pointer_declarator (identifier) @param)))
                (array_declarator (identifier) @param)
                (array_declarator (array_declarator (identifier) @param))
                (function_declarator declarator: (parenthesized_declarator (pointer_declarator (identifier) @param)))
                (function_declarator declarator: (parenthesized_declarator (pointer_declarator (pointer_declarator (identifier) @param))))
              ])

            (declaration
              declarator: [
                (identifier) @var
                (pointer_declarator (identifier) @var)
                (pointer_declarator (pointer_declarator (identifier) @var))
                (pointer_declarator (pointer_declarator (pointer_declarator (identifier) @var)))
                (array_declarator (identifier) @var)
                (array_declarator (array_declarator (identifier) @var))
              ])

            (init_declarator
              declarator: [
                (identifier) @var
                (pointer_declarator (identifier) @var)
                (pointer_declarator (pointer_declarator (identifier) @var))
                (pointer_declarator (pointer_declarator (pointer_declarator (identifier) @var)))
                (array_declarator (identifier) @var)
                (array_declarator (array_declarator (identifier) @var))
              ])

            (for_statement
              initializer: (declaration
                declarator: [
                  (identifier) @var
                  (pointer_declarator (identifier) @var)
                  (init_declarator declarator: (identifier) @var)
                ]))
            """,
        )
    return _VAR_QUERY


def _run_query_captures(query: Query, root_node: Node) -> Dict[str, List[Node]]:
    """Ejecuta una consulta AST abstrayendo diferencias entre versiones de tree-sitter."""
    try:
        if QueryCursor is not None:
            raw = QueryCursor(query).captures(root_node)
        else:
            raw = query.captures(root_node)
    except Exception:
        return {}

    if isinstance(raw, dict):
        return raw
    elif isinstance(raw, list):
        res: Dict[str, List[Node]] = defaultdict(list)
        for item in raw:
            if isinstance(item, tuple) and len(item) == 2:
                node, name = item
                res[name].append(node)
        return res
    return {}


def _find_identifier(node: Optional[Node]) -> Optional[str]:
    """Extrae el identificador de un declarador de forma iterativa y segura."""
    if node is None:
        return None
    try:
        stack = [node]
        while stack:
            curr = stack.pop()
            if curr.type in ("identifier", "type_identifier", "field_identifier"):
                return curr.text.decode("utf-8", errors="replace")
            if curr.type == "function_declarator":
                continue
            for child in reversed(curr.children):
                stack.append(child)
        return None
    except Exception:
        return None


def check_regla_0x0001(content: str) -> List[Tuple[str, int]]:
    """Regla 0x0001h: Extrae variables y argumentos para verificar nombres significativos usando Tree-Sitter AST."""
    variables_found: List[Tuple[str, int]] = []
    try:
        source_bytes = content.encode("utf-8")
        line_starts = _get_line_starts(source_bytes)
        parser = get_c_parser()
        tree = parser.parse(source_bytes)
        query = get_var_query()
        captures = _run_query_captures(query, tree.root_node)

        for cap_name in ("param", "var"):
            for n in captures.get(cap_name, []):
                start = n.start_byte
                end = n.end_byte
                ident = source_bytes[start:end].decode("utf-8", errors="replace")
                if ident and ident.lower() != "void":
                    variables_found.append((ident, _byte_to_line(line_starts, start)))
    except Exception:
        pass

    return sorted(list(set(variables_found)), key=lambda x: x[1])


_RE_VAR_MULTIPLE = re.compile(r'\w+\s+\w+\s*,\s*\w+')
_RE_FOR_START = re.compile(r'^\s*for\s*\(')
_RE_OPERATORS = re.compile(r'[^\s](\+|-|\*|/|%|==|!=|<=|>=|<|>|&&|\|\||&|\||\^|<<|>>|=)[^\s=]')
_RE_INC_DEC = re.compile(r'(\+\+|--)')
_RE_CONTROL_STRUCT = re.compile(r'^\s*\b(if|for|while|switch)\s*\(.*\)')
_RE_GOTO = re.compile(r'\bgoto\b')
_RE_FUNC_DEF = re.compile(r'\w+\s+([a-zA-Z_]\w*)\s*\([^)]*\)\s*\{')
_RE_SNAKE_CASE = re.compile(r'[a-z_][a-z0-9_]*')
_RE_PTR_SPACING = re.compile(r'\w+\s*\*\s+[a-zA-Z_]')
_RE_GETS = re.compile(r'\bgets\s*\(')

_GLOBAL_VAR_QUERY: Optional[Query] = None


def get_global_var_query() -> Query:
    global _GLOBAL_VAR_QUERY
    if _GLOBAL_VAR_QUERY is None:
        _GLOBAL_VAR_QUERY = Query(
            get_c_language(),
            """
            (translation_unit
              (declaration
                type: (_) @type
                declarator: [
                  (identifier) @global_var
                  (pointer_declarator (identifier) @global_var)
                  (pointer_declarator (pointer_declarator (identifier) @global_var))
                  (array_declarator (identifier) @global_var)
                  (init_declarator declarator: (identifier) @global_var)
                  (init_declarator declarator: (pointer_declarator (identifier) @global_var))
                  (init_declarator declarator: (array_declarator (identifier) @global_var))
                ]))
            """,
        )
    return _GLOBAL_VAR_QUERY


def check_regla_0x0002(line: str, line_num: int) -> List[Dict[str, Any]]:
    """Regla 0x0002h: Una declaración de variable por línea."""
    if _RE_FOR_START.match(line):
        return []
    if _RE_VAR_MULTIPLE.search(line):
        return [{
            "rule_id": "0x0002h",
            "line": line_num,
            "severity": "ADVERTENCIA",
            "message": "Se encontraron múltiples declaraciones de variables en una sola línea.",
            "suggestion": "Declarar cada variable en una línea independiente.",
        }]
    return []


def check_regla_0x0004(line: str, line_num: int) -> List[Dict[str, Any]]:
    """Regla 0x0004h: Espacio antes y después de cada operador."""
    if _RE_OPERATORS.search(line):
        if not _RE_INC_DEC.search(line):
            return [{
                "rule_id": "0x0004h",
                "line": line_num,
                "severity": "ESTILO",
                "message": "Falta espacio antes y después de un operador.",
                "suggestion": "Separar operadores con espacios (ej. 'a + b').",
            }]
    return []


def check_regla_0x0005(line: str, line_num: int, lines: List[str]) -> List[Dict[str, Any]]:
    """Regla 0x0005h: Llaves de apertura en línea nueva."""
    line_strip = line.strip()
    match = _RE_CONTROL_STRUCT.match(line_strip)
    if match:
        estructura = match.group(1)
        if '{' in line_strip:
            return [{
                "rule_id": "0x0005h",
                "line": line_num,
                "severity": "ESTILO",
                "message": f"La llave de apertura para `{estructura}` debe estar en una nueva línea.",
                "suggestion": "Ubicar '{' en el renglón siguiente alineada verticalmente.",
            }]
    return []


def check_regla_0x000Bh(content: str) -> List[Dict[str, Any]]:
    """Regla 0x000Bh: Prohibidas las variables globales mutables fuera de funciones usando Tree-Sitter AST."""
    findings = []
    try:
        source_bytes = content.encode("utf-8")
        line_starts = _get_line_starts(source_bytes)
        parser = get_c_parser()
        tree = parser.parse(source_bytes)
        query = get_global_var_query()
        captures = _run_query_captures(query, tree.root_node)

        for n in captures.get("global_var", []):
            parent = n.parent
            while parent and parent.type != "declaration":
                parent = parent.parent
            if parent:
                decl_text = source_bytes[parent.start_byte:parent.end_byte].decode("utf-8", errors="replace")
                if "const " in decl_text or decl_text.startswith("typedef"):
                    continue
            start = n.start_byte
            end = n.end_byte
            ident = source_bytes[start:end].decode("utf-8", errors="replace")
            if ident:
                findings.append({
                    "rule_id": "0x000Bh",
                    "line": _byte_to_line(line_starts, start),
                    "severity": "ERROR",
                    "message": f"Variable global no permitida: '{ident}'.",
                    "suggestion": "Pasar la variable por parámetro o declararla localmente.",
                })
    except Exception:
        pass

    return findings


def check_regla_0x0014h(line: str, line_num: int) -> List[Dict[str, Any]]:
    """Regla 0x0014h: Sin instrucción goto."""
    if _RE_GOTO.search(line):
        return [{
            "rule_id": "0x0014h",
            "line": line_num,
            "severity": "ERROR",
            "message": "Uso de 'goto' no permitido.",
            "suggestion": "Estructurar el flujo mediante funciones y lazos limpios.",
        }]
    return []


def check_regla_0x0017h(line: str, line_num: int) -> List[Dict[str, Any]]:
    """Regla 0x0017h: Funciones en snake_case."""
    match = _RE_FUNC_DEF.match(line)
    if match:
        func_name = match.group(1)
        if not _RE_SNAKE_CASE.fullmatch(func_name) and func_name != 'main':
            return [{
                "rule_id": "0x0017h",
                "line": line_num,
                "severity": "ESTILO",
                "message": f"El nombre de función '{func_name}' no está en snake_case.",
                "suggestion": f"Renombrar en minúsculas separadas por guión bajo (ej. '{func_name.lower()}').",
            }]
    return []


def check_regla_0x0018h(line: str, line_num: int) -> List[Dict[str, Any]]:
    """Regla 0x0018h: Punteros con asterisco pegado al identificador."""
    if _RE_PTR_SPACING.search(line):
        return [{
            "rule_id": "0x0018h",
            "line": line_num,
            "severity": "ESTILO",
            "message": "El asterisco del puntero debe estar junto al identificador (ej. 'int *ptr;').",
            "suggestion": "Escribir 'tipo *nombre_var' en lugar de 'tipo* nombre_var'.",
        }]
    return []


def check_regla_0x001Ch(line: str, line_num: int) -> List[Dict[str, Any]]:
    """Regla 0x001Ch: Prohibido gets."""
    if _RE_GETS.search(line):
        return [{
            "rule_id": "0x001Ch",
            "line": line_num,
            "severity": "ERROR",
            "message": "Uso inseguro de 'gets'.",
            "suggestion": "Utilizar 'fgets(buffer, sizeof(buffer), stdin)'.",
        }]
    return []


def check_regla_0xEEEE(content: str) -> List[Dict[str, Any]]:
    """Regla 0xEEEEh: Indentación de 4 espacios."""
    findings = []
    lines = content.replace('\t', '    ').splitlines()
    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped or stripped.startswith(('#', '//', '/*', '*', '*/')):
            continue
        leading_spaces = len(line) - len(line.lstrip(' '))
        if leading_spaces % 4 != 0:
            findings.append({
                "rule_id": "0xEEEEh",
                "line": i + 1,
                "severity": "ESTILO",
                "message": f"Indentación no es múltiplo de 4 espacios ({leading_spaces} encontrados).",
                "suggestion": "Ajustar indentación a múltiplos de 4 espacios.",
            })
    return findings


def audit_c_file(c_file: Path) -> List[Dict[str, Any]]:
    """Ejecuta el análisis completo de reglas P1 sobre un archivo C usando Tree-Sitter AST."""
    try:
        content = c_file.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        return [{
            "rule_id": "READ_ERROR",
            "file": c_file.name,
            "line": 0,
            "severity": "ERROR",
            "message": str(e),
            "suggestion": "",
        }]

    findings: List[Dict[str, Any]] = []
    lines = content.splitlines()

    # Chequeos de contenido global
    findings.extend(check_regla_0x000Bh(content))
    findings.extend(check_regla_0xEEEE(content))

    # Variables sospechosas (0x0001h)
    vars_found = check_regla_0x0001(content)
    for name, line_num in vars_found:
        if len(name) == 1 and name.lower() not in ("i", "j", "k", "n", "x", "y", "z", "f", "c", "r"):
            findings.append({
                "rule_id": "0x0001h",
                "line": line_num,
                "severity": "ADVERTENCIA",
                "message": f"Identificador de variable no descriptivo de una sola letra '{name}'.",
                "suggestion": "Los nombres de variables deben reflejar con precisión su propósito (salvo índices canónicos i, j, k, n, x, y, z, f, c, r).",
            })
        elif 1 < len(name) < 4 and name.lower() not in ("fd", "fp", "in", "ok"):
            findings.append({
                "rule_id": "0x0001h",
                "line": line_num,
                "severity": "ADVERTENCIA",
                "message": f"Identificador corto y poco expresivo '{name}' ({len(name)} caracteres).",
                "suggestion": "Se recomienda utilizar identificadores más descriptivos del dominio del problema.",
            })
        elif len(name) > 31:
            findings.append({
                "rule_id": "0x0001h",
                "line": line_num,
                "severity": "ADVERTENCIA",
                "message": f"Identificador excesivamente largo '{name}' ({len(name)} caracteres).",
                "suggestion": "Los identificadores no deben superar los 31 caracteres para mantener la legibilidad.",
            })

    # Chequeos línea por línea
    for i, line in enumerate(lines):
        line_num = i + 1
        clean = line.split('//')[0].strip()
        if not clean:
            continue

        findings.extend(check_regla_0x0002(line, line_num))
        findings.extend(check_regla_0x0004(line, line_num))
        findings.extend(check_regla_0x0005(line, line_num, lines))
        findings.extend(check_regla_0x0014h(line, line_num))
        findings.extend(check_regla_0x0017h(line, line_num))
        findings.extend(check_regla_0x0018h(line, line_num))
        findings.extend(check_regla_0x001Ch(line, line_num))

    for f in findings:
        f["file"] = c_file.name
        if "rule_code" not in f and "rule_id" in f:
            f["rule_code"] = f["rule_id"]
        elif "rule_id" not in f and "rule_code" in f:
            f["rule_id"] = f["rule_code"]

    return findings
