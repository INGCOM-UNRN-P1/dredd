"""Linter nativo de reglas de cátedra P1 y verificación estática usando Tree-Sitter AST en Dredd."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Tuple

import tree_sitter_c as tsc
from tree_sitter import Language, Parser, Node

_C_LANGUAGE: Optional[Language] = None
_PARSER: Optional[Parser] = None


def get_c_parser() -> Parser:
    global _C_LANGUAGE, _PARSER
    if _PARSER is None:
        _C_LANGUAGE = Language(tsc.language())
        _PARSER = Parser(_C_LANGUAGE)
    return _PARSER


def _find_identifier(node: Node) -> Optional[str]:
    if node.type in ("identifier", "type_identifier", "field_identifier"):
        return node.text.decode("utf-8", errors="replace")
    for child in node.children:
        res = _find_identifier(child)
        if res:
            return res
    return None


def check_regla_0x0001(content: str) -> List[Tuple[str, int]]:
    """Regla 0x0001h: Extrae variables y argumentos para verificar nombres significativos usando Tree-Sitter AST."""
    variables_found: List[Tuple[str, int]] = []
    source_bytes = content.encode("utf-8")
    parser = get_c_parser()
    tree = parser.parse(source_bytes)

    def _traverse(node: Node) -> None:
        if node.type == "parameter_declaration":
            decl = node.child_by_field_name("declarator")
            if decl:
                ident = _find_identifier(decl)
                if ident and ident.lower() != "void":
                    line_num = node.start_point.row + 1
                    variables_found.append((ident, line_num))

        elif node.type == "declaration":
            # Verificar si es declaración de variable y no de función
            decl = node.child_by_field_name("declarator")
            if decl and decl.type != "function_declarator":
                ident = _find_identifier(decl)
                if ident:
                    line_num = node.start_point.row + 1
                    variables_found.append((ident, line_num))
            elif not decl:
                for child in node.children:
                    if child.type in ("init_declarator", "pointer_declarator", "array_declarator"):
                        ident = _find_identifier(child)
                        if ident:
                            line_num = node.start_point.row + 1
                            variables_found.append((ident, line_num))

        elif node.type == "for_statement":
            init_node = node.child_by_field_name("initializer")
            if init_node:
                for child in init_node.children:
                    if child.type in ("declaration", "init_declarator"):
                        ident = _find_identifier(child)
                        if ident:
                            line_num = node.start_point.row + 1
                            variables_found.append((ident, line_num))

        for child in node.children:
            _traverse(child)

    _traverse(tree.root_node)
    return sorted(list(set(variables_found)), key=lambda x: x[1])


def check_regla_0x0002(line: str, line_num: int) -> List[Dict[str, Any]]:
    """Regla 0x0002h: Una declaración de variable por línea."""
    if re.match(r'\s*for\s*\(', line):
        return []
    if re.search(r'\w+\s+\w+\s*,\s*\w+', line):
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
    operators = r'(\+|-|\*|/|%|==|!=|<=|>=|<|>|&&|\|\||&|\||\^|<<|>>|=)'
    if re.search(r'[^\s]' + operators + r'[^\s=]', line):
        if not re.search(r'(\+\+|--)', line):
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
    control_struct_pattern = re.compile(r'^\s*\b(if|for|while|switch)\s*\(.*\)')
    line_strip = line.strip()
    match = control_struct_pattern.match(line_strip)
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
    source_bytes = content.encode("utf-8")
    parser = get_c_parser()
    tree = parser.parse(source_bytes)

    for node in tree.root_node.children:
        if node.type == "declaration":
            type_node = node.child_by_field_name("type")
            type_text = type_node.text.decode("utf-8", errors="replace") if type_node else ""
            raw_decl = node.text.decode("utf-8", errors="replace")

            # Descartar funciones, typedefs y constantes
            if "const " in raw_decl or raw_decl.startswith("typedef"):
                continue

            decl_node = node.child_by_field_name("declarator")
            if decl_node and decl_node.type == "function_declarator":
                continue

            ident = _find_identifier(decl_node or node)
            if ident:
                findings.append({
                    "rule_id": "0x000Bh",
                    "line": node.start_point.row + 1,
                    "severity": "ERROR",
                    "message": f"Variable global no permitida: '{ident}'.",
                    "suggestion": "Pasar la variable por parámetro o declararla localmente.",
                })

    return findings


def check_regla_0x0014h(line: str, line_num: int) -> List[Dict[str, Any]]:
    """Regla 0x0014h: Sin instrucción goto."""
    if re.search(r'\bgoto\b', line):
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
    match = re.match(r'\w+\s+([a-zA-Z_]\w*)\s*\([^)]*\)\s*{', line)
    if match:
        func_name = match.group(1)
        if not re.fullmatch(r'[a-z_][a-z0-9_]*', func_name) and func_name != 'main':
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
    if re.search(r'\w+\s*\*\s+[a-zA-Z_]', line):
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
    if re.search(r'\bgets\s*\(', line):
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

    return findings
