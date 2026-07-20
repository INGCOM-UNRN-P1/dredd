#!/usr/bin/env python3
"""
Módulo verificador y addon de Cppcheck para evaluar estilo y reglas de programación en C.
Combina la funcionalidad de análisis de estilo lineal y de estructura semántica usando Cppcheck.
"""

import os
import re
import sys
import subprocess
from collections import defaultdict
from pathlib import Path
from shutil import which
from typing import Dict, List, Tuple, Union, Optional

# --- Soporte para ejecutarse como Addon de Cppcheck ---
try:
    import cppcheck
    CPPCHECK_AVAILABLE = True
except ModuleNotFoundError:
    cppcheck = None
    CPPCHECK_AVAILABLE = False


def checker(func):
    """Decorador condicional para registrar funciones como chequeos de cppcheck si está disponible."""
    if CPPCHECK_AVAILABLE and cppcheck:
        return cppcheck.checker(func)
    return func


# --- Reglas AST implementadas como Addon de Cppcheck ---

@checker
def check_globales(cfg, data) -> None:
    """Regla 0x000Bh: No está permitido el uso de variables globales."""
    for token in cfg.tokenlist:
        if token.isName:
            variable = token.variable
            if variable and variable.access == "Global":
                mensaje = f"Regla 0x000Bh: No está permitido el uso de variables globales ({token.str})."
                cppcheck.reportError(token, 'error', mensaje)


@checker
def check_ternario(cfg, data) -> None:
    """Regla 0x0015h: No está permitido el uso del operador ternario '?:'."""
    for tok in cfg.tokenlist:
        if tok.str == "?":
            mensaje = "Regla 0x0015h: No está permitido el uso del operador ternario '?:'."
            cppcheck.reportError(tok, 'error', mensaje)


@checker
def check_lazos(cfg, data) -> None:
    """Regla 0x0006h: No está permitido el uso de 'break' o 'continue' en lazos (excepto en switch)."""
    for tok in cfg.tokenlist:
        if tok.str in ("break", "continue"):
            # Omitir break dentro de un bloque switch
            # En Cppcheck, podemos subir en el scope para verificar si estamos en un switch
            in_switch = False
            scope = tok.scope
            while scope:
                if scope.type == "Switch":
                    in_switch = True
                    break
                scope = scope.nestedIn
            
            if tok.str == "break" and in_switch:
                continue

            mensaje = f"Regla 0x0006h: No está permitido el uso de la manipulación de lazo '{tok.str}'."
            cppcheck.reportError(tok, 'error', mensaje)


@checker
def check_compuesto(cfg, data) -> None:
    """Regla 0x0000h: Evitar operadores compuestos para mayor claridad."""
    for tok in cfg.tokenlist:
        if tok.str in ("/=", "+=", "-=", "%=", "*="):
            mensaje = f"Regla 0x0000h: Se encontró el operador compuesto '{tok.str}'. Prefiera expresiones explícitas (ej. x = x + 1)."
            cppcheck.reportError(tok, 'warn', mensaje)


@checker
def check_retornos(cfg, data) -> None:
    """Regla 0x0008h: Las funciones deben tener un único punto de retorno."""
    for func in cfg.functions:
        return_count = 0
        pila = []
        token = func.token

        while token:
            if token.str == "return":
                return_count += 1

            if token.str == "{":
                pila.append(token.str)
            elif token.str == "}":
                if pila:
                    pila.pop()
                if not pila:
                    break

            token = token.next

        if return_count > 1:
            mensaje = f"Regla 0x0008h: La función '{func.name}' tiene múltiples retornos ({return_count}). Las funciones deben tener un solo punto de salida."
            cppcheck.reportError(func.token, 'error', mensaje)


# --- Reglas de análisis de texto / línea por línea (Verificador) ---

def check_regla_0x0002(line: str, line_num: int) -> List[Tuple[int, str]]:
    """Regla 0x0002h: Una declaración de variable por línea."""
    if re.match(r'\s*for\s*\(', line):
        return []
    if re.search(r'\w+\s+\w+\s*,\s*\w+', line):
        return [(line_num, "Regla 0x0002h: Se encontraron múltiples declaraciones de variables en una sola línea.")]
    return []


def check_regla_0x0004(line: str, line_num: int) -> List[Tuple[int, str]]:
    """Regla 0x0004h: Un espacio antes y después de cada operador."""
    operators = r'(\+|-|\*|/|%|==|!=|<=|>=|<|>|&&|\|\||&|\||\^|<<|>>|=)'
    if re.search(r'[^\s]' + operators + r'[^\s=]', line):
        if not re.search(r'(\+\+|--)', line):
            return [(line_num, "Regla 0x0004h: Falta espacio antes y después de un operador.")]
    if re.search(r'[^\s]\s' + operators + r'[^\s]', line):
        return [(line_num, "Regla 0x0004h: Falta espacio antes de un operador.")]
    if re.search(r'[^\s]' + operators + r'\s[^\s]', line):
        return [(line_num, "Regla 0x0004h: Falta espacio después de un operador.")]
    return []


def check_regla_0x0005(line: str, line_num: int, lines: List[str]) -> List[Tuple[int, str]]:
    """Regla 0x0005h: Todas las estructuras de control van con llaves en línea nueva."""
    control_struct_pattern = re.compile(r'^\s*\b(if|for|while|switch)\s*\(.*\)')
    do_pattern = re.compile(r'^\s*\bdo\b')
    
    line_strip = line.strip()
    match = control_struct_pattern.match(line_strip)
    do_match = do_pattern.match(line_strip)

    if not match and not do_match:
        return []

    if do_match:
        rest_of_line = line_strip[2:].strip()
        if rest_of_line and not rest_of_line.startswith('//'):
             return [(line_num, "Regla 0x0005h: La palabra clave `do` debe estar sola en su línea (excepto comentarios).")]
        if line_num < len(lines):
            if lines[line_num].strip() != '{':
                return [(line_num, "Regla 0x0005h: A un `do` le debe seguir una llave de apertura `{` en una nueva línea.")]
        else:
            return [(line_num, "Regla 0x0005h: Bloque `do` incompleto al final del archivo.")]
        return []

    if match:
        estructura = match.group(1)
        if '{' in line_strip:
            return [(line_num, f"Regla 0x0005h: La llave de apertura para `{estructura}` debe estar en una nueva línea.")]

        # Buscar paréntesis de cierre para detectar sentencias en la misma línea
        open_parens = 0
        last_paren_idx = -1
        in_string_or_char = False
        string_char = ''
        
        start_pos = line_strip.find(estructura)
        first_paren_pos = line_strip.find('(', start_pos)
        
        if first_paren_pos != -1:
            for i in range(first_paren_pos, len(line_strip)):
                char = line_strip[i]
                if in_string_or_char:
                    if char == string_char and (i == 0 or line_strip[i-1] != '\\'):
                        in_string_or_char = False
                elif char in ('"', "'"):
                    in_string_or_char = True
                    string_char = char
                else:
                    if char == '(':
                        open_parens += 1
                    elif char == ')':
                        open_parens -= 1
                
                if open_parens == 0:
                    last_paren_idx = i
                    break

        if last_paren_idx != -1:
            code_after_condition = line_strip[last_paren_idx + 1:].strip()
            if estructura == 'while' and code_after_condition == ';':
                return []
            if code_after_condition and not code_after_condition.startswith('//'):
                return [(line_num, f"Regla 0x0005h: El cuerpo de la estructura `{estructura}` no debe estar en la misma línea que la condición. Use llaves en líneas separadas.")]

        if line_num < len(lines):
            next_line = lines[line_num].strip()
            if next_line != '{':
                return [(line_num, f"Regla 0x0005h: Bloque `{estructura}` debe usar llaves. La llave de apertura '{{' debe estar en la línea siguiente.")]
        else:
            return [(line_num, f"Regla 0x0005h: Bloque `{estructura}` incompleto al final del archivo.")]

    return []


def check_regla_0x000Eh(line: str, line_num: int) -> List[Tuple[int, str]]:
    """Regla 0x000Eh: Los arreglos estáticos solo con tamaño fijo al compilar."""
    if re.search(r'\w+\s+\w+\s*\[\s*[a-zA-Z_]\w*\s*\]', line):
        return [(line_num, "Regla 0x000Eh: Se encontró un arreglo de longitud variable (VLA).")]
    return []


def check_regla_0x0010h(line: str, line_num: int) -> List[Tuple[int, str]]:
    """Regla 0x0010h: Evitar condiciones ambiguas (truthyness)."""
    if re.search(r'\b(if|while)\s*\(\s*[a-zA-Z_]\w*\s*\)', line):
        return [(line_num, "Regla 0x0010h: Condición ambigua. Use una comparación explícita (ej. 'if (var != 0)').")]
    return []


def check_regla_0x0014h(line: str, line_num: int) -> List[Tuple[int, str]]:
    """Regla 0x0014h: Sin instrucción 'goto'."""
    if re.search(r'\bgoto\b', line):
        return [(line_num, "Regla 0x0014h: Se encontró el uso de 'goto'.")]
    return []


def check_regla_0x0017h(line: str, line_num: int) -> List[Tuple[int, str]]:
    """Regla 0x0017h: Nombres de funciones en snake_case."""
    match = re.match(r'\w+\s+([a-zA-Z_]\w*)\s*\([^)]*\)\s*{', line)
    if match:
        func_name = match.group(1)
        if not re.fullmatch(r'[a-z_][a-z0-9_]*', func_name) and func_name != 'main':
            return [(line_num, f"Regla 0x0017h: El nombre de la función '{func_name}' no está en snake_case.")]
    return []


def check_regla_0x0018h(line: str, line_num: int) -> List[Tuple[int, str]]:
    """Regla 0x0018h: Punteros con asterisco pegado al identificador."""
    if re.search(r'\w+\s*\*\s+[a-zA-Z_]', line):
        return [(line_num, "Regla 0x0018h: El asterisco del puntero debe estar junto al nombre de la variable (ej. 'int *ptr;').")]
    return []


def check_regla_0x001Bh(line: str, line_num: int) -> List[Tuple[int, str]]:
    """Regla 0x001Bh: No mezclar asignación y comparación."""
    if re.search(r'\b(if|while)\s*\(.*[^=]=[^=].*\)', line):
        return [(line_num, "Regla 0x001Bh: Se encontró una asignación dentro de una condición.")]
    return []


def check_regla_0x001Ch(line: str, line_num: int) -> List[Tuple[int, str]]:
    """Regla 0x001Ch: Prefieran fgets a gets."""
    if re.search(r'\bgets\s*\(', line):
        return [(line_num, "Regla 0x001Ch: Se encontró el uso de 'gets'. Prefiera 'fgets'.")]
    return []


def check_regla_0x002Eh(line: str, line_num: int) -> List[Tuple[int, str]]:
    """Regla 0x002Eh: Las variables declaradas como const van en MAYÚSCULAS."""
    match = re.search(r'\bconst\s+\w+\s+([a-zA-Z_]\w*)\s*=', line)
    if match:
        const_name = match.group(1)
        if not re.fullmatch(r'[A-Z_][A-Z0-9_]*', const_name):
            return [(line_num, f"Regla 0x002Eh: La constante '{const_name}' no está en MAYUSCULAS_SNAKE_CASE.")]
    return []


def check_regla_0xEEEE(content: str) -> List[Tuple[int, str]]:
    """Regla 0xEEEEh: Indentación de 4 espacios, consistente con el bloque."""
    errors = []
    lines = content.replace('\t', '    ').split('\n')
    indent_level = 0
    
    for i, line in enumerate(lines):
        line_num = i + 1
        stripped_line = line.strip()

        if not stripped_line or stripped_line.startswith(('#', '//', '/*', '*', '*/')):
            continue

        current_check_level = indent_level
        if stripped_line.startswith(('}', 'else', 'case', 'default')):
            if current_check_level > 0:
                current_check_level -= 1
        
        expected_indent = current_check_level * 4
        leading_spaces = len(line) - len(line.lstrip(' '))

        if leading_spaces % 4 != 0:
            errors.append((line_num, f"Regla 0xEEEEh: La indentación debe ser un múltiplo de 4 espacios. Se encontraron {leading_spaces}."))
        elif leading_spaces != expected_indent:
            errors.append((line_num, f"Regla 0xEEEEh: Indentación inconsistente. Se esperaba {expected_indent} espacios, pero se encontraron {leading_spaces}."))

        line_for_braces = re.sub(r'//.*|/\*.*?\*/|"[^"]*"|\'[^\']*\'', '', line)
        indent_level += line_for_braces.count('{') - line_for_braces.count('}')
        if indent_level < 0:
            indent_level = 0
            
    return errors


def check_regla_0x0001(content: str) -> List[Tuple[str, int]]:
    """Regla 0x0001h: Extrae variables y argumentos para verificar nombres significativos."""
    variables_found = []
    lines = content.split('\n')
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


def check_regla_0x0030h(line: str, line_num: int) -> List[Tuple[int, str]]:
    """Regla 0x0030h: Identificadores de variables y argumentos en snake_case."""
    errors = []
    snake_case_pattern = re.compile(r'^[a-z_][a-z0-9_]*$')
    clean_line = line.split('//')[0]

    if not clean_line.strip() or clean_line.strip().startswith('#') or re.search(r'\bconst\b', clean_line):
        return []
    
    for_loop_match = re.search(r'for\s*\(([^;]+);', clean_line)
    if for_loop_match:
        init_part = for_loop_match.group(1).strip()
        type_pattern = r'\b(int|char|float|double|short|long|unsigned|signed|struct\s+\w+)\b'
        if re.search(type_pattern, init_part):
            var_name_part = init_part.split('=')[0].strip()
            parts = var_name_part.split()
            if parts:
                var_name = parts[-1].lstrip('*').split('[')[0]
                if var_name and not snake_case_pattern.fullmatch(var_name):
                    errors.append((line_num, f"Regla 0x0030h: La variable '{var_name}' en el bucle for no está en snake_case."))

    func_match = re.search(r'\(([^)]*)\)\s*{', clean_line)
    if func_match:
        params_str = func_match.group(1).strip()
        if params_str and params_str.lower() != 'void':
            for param in params_str.split(','):
                parts = param.strip().split()
                if parts:
                    var_name = parts[-1].lstrip('*').split('[')[0]
                    if var_name and not snake_case_pattern.fullmatch(var_name):
                        errors.append((line_num, f"Regla 0x0030h: El argumento '{var_name}' no está en snake_case."))

    var_decl_match = re.search(r'^\s*(?:static|extern|unsigned|signed|struct)?\s*\w+\s+([^;]+);', clean_line)
    if var_decl_match:
        declarations_str = var_decl_match.group(1)
        if '(' not in declarations_str or ')' not in declarations_str:
            for decl in declarations_str.split(','):
                var_name = decl.strip().split('=')[0].strip().split('[')[0].strip()
                if ' ' in var_name:
                     var_name = var_name.split()[-1]
                var_name = var_name.lstrip('*')
                if var_name and not snake_case_pattern.fullmatch(var_name):
                    errors.append((line_num, f"Regla 0x0030h: La variable '{var_name}' no está en snake_case."))

    return errors


def check_regla_0x0009(content: str) -> Dict[str, Dict[str, int]]:
    """Regla 0x0009h: Las funciones no van con I/O a consola (printf, scanf, etc.)."""
    io_functions_in_code = {}
    io_keywords = ['printf', 'scanf', 'puts', 'gets', 'putchar', 'getchar']
    function_pattern = re.compile(r'(\w[\w\s\*]+\([^\)]*\))\s*{', re.MULTILINE)
    
    for func_match in function_pattern.finditer(content):
        func_signature = " ".join(func_match.group(1).strip().split())
        if 'main' in func_signature:
            continue

        start_index = func_match.end()
        open_braces = 1
        end_index = -1
        for i, char in enumerate(content[start_index:]):
            if char == '{':
                open_braces += 1
            elif char == '}':
                open_braces -= 1
                if open_braces == 0:
                    end_index = start_index + i
                    break
        
        if end_index != -1:
            function_body = content[start_index:end_index]
            io_counts = {}
            for keyword in io_keywords:
                matches = re.findall(fr'\b{keyword}\b', function_body)
                if matches:
                    io_counts[keyword] = len(matches)
            if io_counts:
                io_functions_in_code[func_signature] = io_counts
                
    return io_functions_in_code


def check_regla_0x000A(content: str) -> List[Tuple[str, Optional[str], int]]:
    """Regla 0x000Ah: Revisa que todas las funciones posean comentarios de documentación."""
    
    def capture_preceding_comment(lines: List[str], func_line_index: int) -> Optional[str]:
        comment_lines = []
        current_index = func_line_index - 1

        while current_index >= 0 and not lines[current_index].strip():
            current_index -= 1

        if current_index < 0:
            return None
        line = lines[current_index].strip()

        if line.endswith('*/'):
            comment_lines.append(lines[current_index])
            if not line.startswith('/*'):
                current_index -= 1
                while current_index >= 0:
                    prev_line = lines[current_index]
                    comment_lines.append(prev_line)
                    if prev_line.strip().startswith('/*'):
                        return "\n".join(reversed(comment_lines))
                    current_index -= 1
            else:
                 return "\n".join(reversed(comment_lines))

        elif line.startswith('//'):
            comment_lines.append(lines[current_index])
            current_index -= 1
            while current_index >= 0:
                prev_line_stripped = lines[current_index].strip()
                if prev_line_stripped.startswith('//'):
                    comment_lines.append(lines[current_index])
                    current_index -= 1
                else:
                    break
            return "\n".join(reversed(comment_lines))
        return None

    functions_with_docs = []
    lines = content.split('\n')
    func_pattern = re.compile(r'^\s*(\w[\w\s\*]+\([^\)]*\))\s*[;{]')
    brace_level = 0

    for i, line in enumerate(lines):
        if brace_level == 0:
            match = func_pattern.match(line.strip())
            if match:
                full_signature = " ".join(match.group(1).strip().split())
                comment = capture_preceding_comment(lines, i)
                functions_with_docs.append((full_signature, comment, i + 1))
        
        brace_level += line.count('{') - line.count('}')
            
    unique_functions = {}
    for sig, doc, line_num in functions_with_docs:
        if sig not in unique_functions or unique_functions[sig][0] is None:
             unique_functions[sig] = (doc, line_num)

    return sorted([(sig, data[0], data[1]) for sig, data in unique_functions.items()])


# --- Procesamiento e integración ---

def compile_file(filepath: Path) -> str:
    """Compila un archivo C con GCC y retorna la salida de stderr."""
    command = [
        'gcc', '-Wall', '-Wextra', '-std=c23', '-pedantic',
        '-Wmissing-prototypes', '-Wstrict-prototypes', '-fanalyzer',
        str(filepath), '-o', os.devnull
    ]
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=15)
        return result.stderr
    except FileNotFoundError:
        return "Error: GCC no se encuentra en el PATH."
    except subprocess.TimeoutExpired:
        return "Error: Tiempo de compilación excedido (15s)."
    except Exception as e:
        return f"Error inesperado en compilación: {e}"


def run_cppcheck(filepath: Path) -> str:
    """Ejecuta Cppcheck utilizando este mismo script unificado como addon."""
    current_script = Path(__file__).resolve()
    command = [
        'cppcheck',
        '--enable=all',
        f'--addon={current_script}',
        '--check-level=exhaustive',
        '--suppress=missingIncludeSystem',
        '--template=[{severity}] {file}:{line}: {id}: {message}',
        str(filepath)
    ]
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=20)
        return result.stderr
    except FileNotFoundError:
        return "Error: Cppcheck no se encuentra en el PATH."
    except subprocess.TimeoutExpired:
        return "Error: Tiempo de Cppcheck excedido (20s)."
    except Exception as e:
        return f"Error al ejecutar Cppcheck: {e}"


def analyze_file(filepath: Path) -> Dict[str, Union[List, Dict, str]]:
    """Analiza un archivo de C y devuelve el reporte estructurado de fallas y estilo."""
    errors = []
    file_content = ""
    encodings = ['utf-8', 'latin-1', 'cp1252']
    
    for encoding in encodings:
        try:
            with open(filepath, 'r', encoding=encoding) as f:
                file_content = f.read()
            break
        except UnicodeDecodeError:
            continue
        except Exception as e:
            msg = f"Error al leer archivo: {e}"
            return {'errors': [(0, msg)], 'variables': [], 'io_functions': {}, 'functions_documentation': [], 'content': msg}

    if not file_content:
        msg = f"No se pudo decodificar el archivo {filepath.name}."
        return {'errors': [(0, msg)], 'variables': [], 'io_functions': {}, 'functions_documentation': [], 'content': msg}

    lines = file_content.split('\n')
    
    variables_info = check_regla_0x0001(file_content)
    io_functions_info = check_regla_0x0009(file_content)
    functions_documentation_info = check_regla_0x000A(file_content)
    errors.extend(check_regla_0xEEEE(file_content))

    for i, line in enumerate(lines):
        line_num = i + 1
        errors.extend(check_regla_0x0002(line, line_num))
        errors.extend(check_regla_0x0004(line, line_num))
        errors.extend(check_regla_0x0005(line, line_num, lines))
        errors.extend(check_regla_0x000Eh(line, line_num))
        errors.extend(check_regla_0x0010h(line, line_num))
        errors.extend(check_regla_0x0014h(line, line_num))
        errors.extend(check_regla_0x0017h(line, line_num))
        errors.extend(check_regla_0x0018h(line, line_num))
        errors.extend(check_regla_0x001Bh(line, line_num))
        errors.extend(check_regla_0x001Ch(line, line_num))
        errors.extend(check_regla_0x002Eh(line, line_num))
        errors.extend(check_regla_0x0030h(line, line_num))
        
    return {
        'errors': errors, 
        'variables': variables_info, 
        'io_functions': io_functions_info,
        'functions_documentation': functions_documentation_info,
        'content': file_content
    }


def main() -> None:
    """Orquestador principal para analizar directorios de estudiantes."""
    if len(sys.argv) != 2:
        print("Uso: python verificador.py <ruta_al_directorio_base>")
        sys.exit(1)

    base_folder = Path(sys.argv[1])
    if not base_folder.is_dir():
        print(f"Error: La ruta '{base_folder}' no es una carpeta válida.")
        sys.exit(1)

    cppcheck_installed = which('cppcheck') is not None
    if not cppcheck_installed:
        print("Advertencia: 'cppcheck' no está instalado en el PATH. Se omitirá el análisis estructural.")

    for student_dir in sorted(base_folder.iterdir()):
        if not student_dir.is_dir():
            continue

        student_name = student_dir.name
        report_content = (
            f"# Informe de Estilo para: {student_name}\n\n"
            "**OBSERVACIÓN IMPORTANTE**\nEsto es una verificación automática de las reglas.\n"
        )
        
        c_files = sorted(student_dir.glob("**/*.c"))
        if not c_files:
            report_content += "No se encontraron archivos `.c` para analizar en este directorio.\n"
        
        for filepath in c_files:
            analysis = analyze_file(filepath)
            relative_filepath = filepath.relative_to(student_dir)
            
            report_content += (
                f"## Verificando: `{relative_filepath}`\n\n"
                "```c\n"
                f"{analysis['content']}\n"
                "```\n\n"
                "### Estilo\n\n"
            )

            errors = analysis['errors']
            variables = analysis['variables']
            io_functions = analysis['io_functions']
            funcs_documentation = analysis['functions_documentation']
            
            has_issues = any([errors, variables, io_functions, funcs_documentation])

            if not has_issues:
                report_content += "No se encontraron problemas de estilo en este archivo.\n\n"
            else:
                if variables:
                    report_content += "#### Regla 0x0001h: Nombres de Variables Significativos\n\n"
                    suspicious_found = False
                    for name, line_num in variables:
                        if len(name) < 4:
                            report_content += f"- **Línea {line_num}:** `{name}` - **Variable sospechosa**\n"
                            suspicious_found = True
                        else:
                            report_content += f"- **Línea {line_num}:** `{name}`\n"
                    if not suspicious_found:
                         report_content += "\nTodos los identificadores parecen descriptivos a simple vista.\n"
                    report_content += "\n"

                if io_functions:
                    report_content += "#### Regla `0x0009h`: Las funciones no van con `printf` o `scanf`, a no ser que ese sea su propósito\n\n"
                    for func_sig, counts in io_functions.items():
                        counts_str = ", ".join([f"{count}:`{func}`" for func, count in sorted(counts.items())])
                        report_content += f"\n\n`{func_sig}` {counts_str}\n"
                    report_content += "\n"
                
                if funcs_documentation:
                    report_content += "#### Regla `0x000Ah`: Revisión de Documentación de Funciones\n\n"
                    for func_sig, comment, line_num in funcs_documentation:
                        report_content += f"##### Firma: `{func_sig}`\n\n"
                        if comment:
                            report_content += (
                                "**Comentario Encontrado:**\n\n"
                                f"```c\n{comment}\n{func_sig}\n```\n\n"
                            )
                        else:
                            report_content += f"**ADVERTENCIA (Línea {line_num}):** No se encontró un comentario de documentación para esta función/prototipo.\n\n"
                        report_content += "---\n"

                if errors:
                    errors_by_rule = defaultdict(list)
                    for line_num, msg in sorted(errors):
                        rule = msg.split(':')[0]
                        errors_by_rule[rule].append((line_num, msg))
                    
                    for rule in sorted(errors_by_rule.keys()):
                        report_content += f"#### {rule}\n"
                        for line_num, msg in errors_by_rule[rule]:
                             report_content += f"- **Línea {line_num}:** {msg.split(':', 1)[1].strip()}\n"
                        report_content += "\n"
            
            report_content += "### Resultado de Compilación (GCC)\n\n"
            compilation_output = compile_file(filepath)
            if compilation_output.strip():
                report_content += f"```text\n{compilation_output.strip()}\n```\n\n"
            else:
                report_content += "Compilación exitosa sin advertencias.\n\n"
            
            if cppcheck_installed:
                report_content += "### Análisis con Cppcheck (con Reglas de Estilo AST)\n\n"
                cppcheck_output = run_cppcheck(filepath)
                if cppcheck_output.strip():
                    report_content += f"```text\n{cppcheck_output.strip()}\n```\n\n"
                else:
                    report_content += "Cppcheck no encontró problemas.\n\n"

        report_path = student_dir / f"{student_name}.md"
        try:
            with open(report_path, "w", encoding="utf-8") as report_file:
                report_file.write(report_content)
            print(f"Análisis completado para '{student_name}'. Informe guardado en: '{report_path}'")
        except IOError as e:
            print(f"Error al escribir el informe para '{student_name}': {e}")


if __name__ == "__main__":
    main()
