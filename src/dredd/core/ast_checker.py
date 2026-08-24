"""Linter nativo de reglas de cátedra P1 y verificación estática en Python para Dredd."""

from collections import defaultdict
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Tuple


def check_regla_0x0001(content: str) -> List[Tuple[str, int]]:
    """Regla 0x0001h: Extrae variables y argumentos para verificar nombres significativos."""
    variables_found = []
    lines = content.splitlines()
    func_def_pattern = re.compile(r'\w[\w\s\*]+\s*\(([^)]*)\)\s*{')
    var_decl_pattern = re.compile(r'^\s*(?:const|static|extern|unsigned|signed|struct\s+\w+|void|int|char|float|double|short|long)\s+([^;]+);')
    for_loop_decl_pattern = re.compile(r'for\s*\(([^;]+);')

    for i, line in enumerate(lines):
        line_num = i + 1
        clean_line = line.split('//')[0].strip()
        if not clean_line or clean_line.startswith('#'):
            continue

        for_match = for_loop_decl_pattern.search(clean_line)
        if for_match:
            init_part = for_match.group(1).strip()
            type_pattern = r'\b(const|static|extern|unsigned|signed|struct\s+\w+|void|int|char|float|double|short|long)\b'
            if re.search(type_pattern, init_part):
                var_name_part = init_part.split('=')[0].strip()
                parts = var_name_part.split()
                if parts:
                    var_name = parts[-1].lstrip('*').split('[')[0]
                    if var_name:
                        variables_found.append((var_name, line_num))

        match = func_def_pattern.search(clean_line)
        if match:
            params_str = match.group(1).strip()
            if params_str and params_str.lower() != 'void':
                for param in params_str.split(','):
                    parts = param.strip().split()
                    if parts:
                        var_name = parts[-1].lstrip('*').split('[')[0]
                        if var_name:
                            variables_found.append((var_name, line_num))
        elif not ('(' in clean_line and ')' in clean_line and '{' not in clean_line):
            match = var_decl_pattern.search(clean_line)
            if match:
                declarations_str = match.group(1)
                if '(' in declarations_str and ')' in declarations_str:
                    continue
                for decl in declarations_str.split(','):
                    if '=' in decl:
                        decl = decl.split('=')[0]
                    if '[' in decl:
                        decl = decl.split('[')[0]
                    parts = decl.strip().split()
                    if parts:
                        var_name = parts[-1].lstrip('*')
                        if var_name:
                            variables_found.append((var_name, line_num))

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
    """Regla 0x000Bh: Prohibidas las variables globales mutables fuera de funciones."""
    findings = []
    lines = content.splitlines()
    brace_level = 0
    var_pattern = re.compile(r'^\s*(?:static\s+)?(?:int|char|float|double|short|long|unsigned|struct\s+\w+)\s+([a-zA-Z_]\w*)\s*(?:=|;)')

    for i, line in enumerate(lines):
        clean = line.split('//')[0].strip()
        if not clean or clean.startswith('#'):
            continue

        if brace_level == 0 and not clean.endswith(';'):
            # Posible inicio de función o struct
            pass
        elif brace_level == 0 and clean.endswith(';'):
            m = var_pattern.match(clean)
            if m and not clean.startswith('typedef') and not clean.startswith('const'):
                findings.append({
                    "rule_id": "0x000Bh",
                    "line": i + 1,
                    "severity": "ERROR",
                    "message": f"Variable global no permitida: '{m.group(1)}'.",
                    "suggestion": "Pasar la variable por parámetro o declararla localmente.",
                })

        brace_level += clean.count('{') - clean.count('}')
        if brace_level < 0:
            brace_level = 0

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
    """Ejecuta el análisis completo de reglas P1 sobre un archivo C."""
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
        if len(name) < 3 and name not in ("i", "j", "k", "n", "fd", "fp"):
            findings.append({
                "rule_id": "0x0001h",
                "line": line_num,
                "severity": "ADVERTENCIA",
                "message": f"Identificador muy corto o poco descriptivo: '{name}'.",
                "suggestion": "Usar un nombre autoexplicativo (ej. 'contador', 'indice').",
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
