import os
import sys
import re
import subprocess
from collections import defaultdict
from shutil import which

# --- Helper para verificar herramientas ---

def is_tool_installed(name):
    """Verifica si una herramienta está en el PATH y es ejecutable."""
    return which(name) is not None

# --- Definiciones de las Reglas ---

def check_regla_0x0000(line, line_num):
    """Regla 0x0000h: Claridad y prolijidad (sin operadores compuestos)."""
    compound_operators = r'(\+=|-=|\*=|/=|%=|&=|\|=|\^=|<<=|>>=)'
    line_no_comments = line.split('//')[0]
    if re.search(compound_operators, line_no_comments):
        return [(line_num, "Regla 0x0000h: Se encontró un operador compuesto. Prefiera expresiones explícitas para mayor claridad (ej. `x = x + 1` en lugar de `x += 1`).")]
    return []

def check_regla_0x0001(content):
    """
    Regla 0x0001h: Nombres de variables significativos.
    Encuentra todas las variables y argumentos y devuelve una lista de tuplas (nombre, numero_linea).
    """
    variables_found = []
    lines = content.split('\n')
    func_def_pattern = re.compile(r'\w[\w\s\*]+\s*\(([^)]*)\)\s*{')
    # Regex mejorada para detectar tipos comunes, incluyendo 'struct <nombre>'
    var_decl_pattern = re.compile(r'^\s*(?:const|static|extern|unsigned|signed|struct\s+\w+|void|int|char|float|double|short|long)\s+([^;]+);')
    # --- MEJORA: Patrón para detectar declaraciones en bucles for ---
    for_loop_decl_pattern = re.compile(r'for\s*\(([^;]+);')

    for i, line in enumerate(lines):
        line_num = i + 1
        clean_line = line.split('//')[0].strip()
        if not clean_line or clean_line.startswith('#'):
            continue

        # --- MEJORA: Manejar declaraciones en bucles for ---
        for_match = for_loop_decl_pattern.search(clean_line)
        if for_match:
            init_part = for_match.group(1).strip()
            # Verificar si es una declaración buscando un tipo de dato
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
                params = params_str.split(',')
                for param in params:
                    param = param.strip()
                    parts = param.split()
                    if parts:
                        var_name = parts[-1].lstrip('*').split('[')[0]
                        if var_name:
                            variables_found.append((var_name, line_num))
        
        # Excluir prototipos de funciones y llamadas a funciones de forma más segura
        elif not ('(' in clean_line and ')' in clean_line and '{' not in clean_line):
            match = var_decl_pattern.search(clean_line)
            if match:
                declarations_str = match.group(1)
                # Excluir si parece una llamada a función dentro de la declaración (caso borde)
                if '(' in declarations_str and ')' in declarations_str:
                    continue
                
                declarations = declarations_str.split(',')
                for decl in declarations:
                    # Lógica de parseo mejorada y más clara para obtener el nombre
                    # 1. Quitar la parte de la inicialización
                    if '=' in decl:
                        decl = decl.split('=')[0]
                    
                    # 2. Quitar la parte de la definición de array
                    if '[' in decl:
                        decl = decl.split('[')[0]

                    # 3. El nombre es la última palabra que queda
                    parts = decl.strip().split()
                    if parts:
                        var_name = parts[-1]
                        # 4. Quitar los asteriscos de puntero del nombre
                        var_name = var_name.lstrip('*')
                        if var_name:
                            variables_found.append((var_name, line_num))
                            
    return sorted(list(set(variables_found)), key=lambda x: x[1])

def check_regla_0x0002(line, line_num):
    """Regla 0x0002h: Una declaración de variable por línea."""
    if re.match(r'\s*for\s*\(', line):
        return []
    if re.search(r'\w+\s+\w+\s*,\s*\w+', line):
        return [(line_num, "Regla 0x0002h: Se encontraron múltiples declaraciones de variables en una sola línea.")]
    return []

def check_regla_0x0004(line, line_num):
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

def check_regla_0x0005(line, line_num, lines):
    """Regla 0x0005h: Todas las estructuras de control van con llaves en línea nueva."""
    # Este regex encuentra estructuras de control que son seguidas por paréntesis.
    control_struct_pattern = re.compile(r'^\s*\b(if|for|while|switch)\s*\(.*\)')
    # 'do' es más simple y no usa paréntesis en su línea.
    do_pattern = re.compile(r'^\s*\bdo\b')
    
    line_strip = line.strip()

    match = control_struct_pattern.match(line_strip)
    do_match = do_pattern.match(line_strip)

    # Si no es una línea de estructura de control, salir.
    if not match and not do_match:
        return []

    # --- Caso 1: palabra clave 'do' ---
    if do_match:
        # Verificar si hay algo más en la misma línea que 'do' (excepto comentarios)
        rest_of_line = line_strip[len('do'):].strip()
        if rest_of_line and not rest_of_line.startswith('//'):
             return [(line_num, "Regla 0x0005h: La palabra clave `do` debe estar sola en su línea (excepto comentarios).")]
        # Verificar que la siguiente línea no vacía sea una llave de apertura
        if line_num < len(lines):
            if lines[line_num].strip() != '{':
                return [(line_num, "Regla 0x0005h: A un `do` le debe seguir una llave de apertura `{` en una nueva línea.")]
        else: # 'do' es la última línea del archivo
            return [(line_num, "Regla 0x0005h: Bloque `do` incompleto al final del archivo.")]
        return [] # 'do' parece correcto

    # --- Caso 2: if, for, while, switch ---
    if match:
        estructura = match.group(1)
        
        # Verificar si hay una llave de apertura en la misma línea (ej. "if(...) {")
        if '{' in line_strip:
            return [(line_num, f"Regla 0x0005h: La llave de apertura para `{estructura}` debe estar en una nueva línea.")]

        # Encontrar el paréntesis de cierre de la condición para verificar si hay código en la misma línea.
        open_parens = 0
        last_paren_idx = -1
        in_string_or_char = False
        string_char = ''
        
        # Empezar la búsqueda después de la palabra clave
        start_pos = line_strip.find(estructura)
        first_paren_pos = line_strip.find('(', start_pos)
        
        if first_paren_pos != -1:
            for i in range(first_paren_pos, len(line_strip)):
                char = line_strip[i]
                
                if in_string_or_char:
                    if char == string_char and (i == 0 or line_strip[i-1] != '\\'):
                        in_string_or_char = False
                elif char == '"' or char == "'":
                    in_string_or_char = True
                    string_char = char
                elif not in_string_or_char:
                    if char == '(': open_parens += 1
                    elif char == ')': open_parens -= 1
                
                if open_parens == 0:
                    last_paren_idx = i
                    break

        if last_paren_idx != -1:
            code_after_condition = line_strip[last_paren_idx + 1:].strip()
            
            # Heurística para permitir bucles `do-while`, que terminan en `while(...);`
            if estructura == 'while' and code_after_condition == ';':
                return [] # Asumir que es un do-while válido y no seguir verificando.

            # Esta es la verificación principal para el problema del usuario: `if(...) statement;`
            if code_after_condition and not code_after_condition.startswith('//'):
                return [(line_num, f"Regla 0x0005h: El cuerpo de la estructura `{estructura}` no debe estar en la misma línea que la condición. Use llaves en líneas separadas.")]

        # Si la línea está bien, verificar que la siguiente línea tenga la llave de apertura.
        if line_num < len(lines):
            next_line = lines[line_num].strip()
            if next_line != '{':
                return [(line_num, f"Regla 0x0005h: Bloque `{estructura}` debe usar llaves. La llave de apertura '{'{'}' debe estar en la línea siguiente.")]
        else: # Es la última línea del archivo
            return [(line_num, f"Regla 0x0005h: Bloque `{estructura}` incompleto al final del archivo. Falta el cuerpo con llaves.")]

    return []

def check_regla_0x0006(line, line_num):
    """Regla 0x0006h: Sin 'break' o 'continue' en lazos."""
    if re.search(r'\b(break|continue)\b', line):
        return [(line_num, "Regla 0x0006h: Se encontró el uso de 'break' o 'continue'.")]
    return []

def check_regla_0x0008(content):
    """Regla 0x0008h: Una sola instrucción 'return' por función."""
    errors = []
    function_pattern = re.compile(r'\w+\s+\w+\s*\([^)]*\)\s*{', re.MULTILINE)
    functions = function_pattern.finditer(content)
    
    for func_match in functions:
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
            function_body_lines = function_body.split('\n')
            body_start_line = content[:start_index].count('\n') + 1
            
            return_lines = []
            for i, line in enumerate(function_body_lines):
                if re.search(r'\breturn\b', line):
                    return_lines.append(body_start_line + i)
            
            if len(return_lines) > 1:
                # Reportar cada 'return' después del primero como un error individual
                for i in range(1, len(return_lines)):
                    line_num = return_lines[i]
                    errors.append((line_num, f"Regla 0x0008h: Instrucción `return` adicional. Las funciones deben tener un solo punto de salida."))
    return errors

def check_regla_0x0009(content):
    """
    Regla 0x0009h: Las funciones no van con I/O a consola, a no ser que ese sea su propósito.
    Devuelve un diccionario con las funciones que usan I/O y el conteo de cada llamada.
    """
    io_functions_in_code = {}
    io_keywords = ['printf', 'scanf', 'puts', 'gets', 'putchar', 'getchar']
    function_pattern = re.compile(r'(\w[\w\s\*]+\([^\)]*\))\s*{', re.MULTILINE)
    functions = function_pattern.finditer(content)

    for func_match in functions:
        func_signature = " ".join(func_match.group(1).strip().split())
        if 'main' in func_signature:
            continue

        start_index = func_match.end()
        open_braces = 1
        end_index = -1
        for i, char in enumerate(content[start_index:]):
            if char == '{': open_braces += 1
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

def check_regla_0x000A(content):
    """
    Regla 0x000Ah: Revisa la documentación de todas las funciones.
    Devuelve una lista de tuplas (firma, comentario, linea), donde comentario es None si está ausente.
    """
    
    def capture_preceding_comment(lines, func_line_index):
        comment_lines = []
        current_index = func_line_index - 1

        while current_index >= 0 and not lines[current_index].strip():
            current_index -= 1

        if current_index < 0: return None
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
                else: break
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
        
        if '{' in line:
            brace_level += line.count('{')
        if '}' in line:
            brace_level -= line.count('}')
            
    unique_functions = {}
    for sig, doc, line_num in functions_with_docs:
        if sig not in unique_functions or (sig in unique_functions and unique_functions[sig][0] is None):
             unique_functions[sig] = (doc, line_num)

    return sorted([(sig, data[0], data[1]) for sig, data in unique_functions.items()])


def check_regla_0x000B(line, line_num, in_function):
    """Regla 0x000Bh: Sin usar variables globales."""
    if not in_function and re.match(r'\s*(int|char|float|double|short|long|void|struct)\s+\w+', line):
         if not re.search(r'\(.*\)', line):
            return [(line_num, "Regla 0x000Bh: Se detectó una posible variable global.")]
    return []

def check_regla_0x000E(line, line_num):
    """Regla 0x000Eh: Los arreglos estáticos solo con tamaño fijo al compilar."""
    if re.search(r'\w+\s+\w+\s*\[\s*[a-zA-Z_]\w*\s*\]', line):
        return [(line_num, "Regla 0x000Eh: Se encontró un arreglo de longitud variable (VLA).")]
    return []

def check_regla_0x0010(line, line_num):
    """Regla 0x0010h: Evitar condiciones ambiguas (truthyness)."""
    if re.search(r'\b(if|while)\s*\(\s*[a-zA-Z_]\w*\s*\)', line):
        return [(line_num, "Regla 0x0010h: Condición ambigua. Use una comparación explícita (ej. 'if (var != 0)').")]
    return []

def check_regla_0x0014(line, line_num):
    """Regla 0x0014h: Sin instrucción 'goto'."""
    if re.search(r'\bgoto\b', line):
        return [(line_num, "Regla 0x0014h: Se encontró el uso de 'goto'.")]
    return []

def check_regla_0x0015(line, line_num):
    """Regla 0x0015h: Sin operador condicional (ternario) '?:'."""
    if re.search(r'\?\s*.*\s*:', line):
        return [(line_num, "Regla 0x0015h: Se encontró el uso del operador ternario '?:'.")]
    return []
    
def check_regla_0x0017(line, line_num):
    """Regla 0x0017h: Nombres de funciones en snake_case."""
    match = re.match(r'\w+\s+([a-zA-Z_]\w*)\s*\([^)]*\)\s*{', line)
    if match:
        func_name = match.group(1)
        if not re.fullmatch(r'[a-z_][a-z0-9_]*', func_name) and func_name != 'main':
            return [(line_num, f"Regla 0x0017h: El nombre de la función '{func_name}' no está en snake_case.")]
    return []

def check_regla_0x0018(line, line_num):
    """Regla 0x0018h: Punteros con asterisco pegado al identificador."""
    if re.search(r'\w+\s*\*\s+[a-zA-Z_]', line):
        return [(line_num, "Regla 0x0018h: El asterisco del puntero debe estar junto al nombre de la variable (ej. 'int *ptr;').")]
    return []

def check_regla_0x001B(line, line_num):
    """Regla 0x001Bh: No mezclar asignación y comparación."""
    if re.search(r'\b(if|while)\s*\(.*[^=]=[^=].*\)', line):
        return [(line_num, "Regla 0x001Bh: Se encontró una asignación dentro de una condición.")]
    return []

def check_regla_0x001C(line, line_num):
    """Regla 0x001Ch: Prefieran fgets a gets."""
    if re.search(r'\bgets\s*\(', line):
        return [(line_num, "Regla 0x001Ch: Se encontró el uso de 'gets'. Prefiera 'fgets'.")]
    return []

def check_regla_0x002E(line, line_num):
    """Regla 0x002Eh: Las variables declaradas como const van en MAYUSCULAS."""
    match = re.search(r'\bconst\s+\w+\s+([a-zA-Z_]\w*)\s*=', line)
    if match:
        const_name = match.group(1)
        if not re.fullmatch(r'[A-Z_][A-Z0-9_]*', const_name):
            return [(line_num, f"Regla 0x002Eh: La constante '{const_name}' no está en MAYUSCULAS_SNAKE_CASE.")]
    return []

def check_regla_0x0030h(line, line_num):
    """Regla 0x0030h: Identificadores de variables y argumentos en snake_case."""
    errors = []
    snake_case_pattern = re.compile(r'^[a-z_][a-z0-9_]*$')
    clean_line = line.split('//')[0]

    if not clean_line.strip() or clean_line.strip().startswith('#'):
        return []
    
    if re.search(r'\bconst\b', clean_line):
        return []

    # --- MEJORA: Manejar declaraciones en bucles for ---
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
            params = params_str.split(',')
            for param in params:
                param = param.strip()
                parts = param.split()
                if parts:
                    var_name = parts[-1].lstrip('*').split('[')[0]
                    if var_name and not snake_case_pattern.fullmatch(var_name):
                        errors.append((line_num, f"Regla 0x0030h: El argumento '{var_name}' no está en snake_case."))

    var_decl_match = re.search(r'^\s*(?:static|extern|unsigned|signed|struct)?\s*\w+\s+([^;]+);', clean_line)
    if var_decl_match:
        declarations_str = var_decl_match.group(1)
        if '(' in declarations_str and ')' in declarations_str:
            return errors

        declarations = declarations_str.split(',')
        for decl in declarations:
            var_name = decl.strip().split('=')[0].strip().split('[')[0].strip()
            if ' ' in var_name:
                 var_name = var_name.split()[-1]
            var_name = var_name.lstrip('*')
            
            if var_name and not snake_case_pattern.fullmatch(var_name):
                errors.append((line_num, f"Regla 0x0030h: La variable '{var_name}' no está en snake_case."))

    return errors

def check_regla_0xEEEE(content):
    """Regla 0xEEEEh: Indentación de 4 espacios, consistente con el bloque."""
    errors = []
    # Reemplazar tabs con 4 espacios para un análisis consistente
    lines = content.replace('\t', '    ').split('\n')
    indent_level = 0
    
    for i, line in enumerate(lines):
        line_num = i + 1
        stripped_line = line.strip()

        # Ignorar líneas vacías, comentarios de una sola línea y directivas de preprocesador
        if not stripped_line or stripped_line.startswith('#') or stripped_line.startswith('//'):
            continue
        
        # Ignorar comentarios multilínea por simplicidad (pueden tener su propio formato)
        if stripped_line.startswith(('/*', '*', '*/')):
            continue

        # Una línea con una llave de cierre (o 'else', 'case') debe estar desindentada
        # al nivel del bloque que la contiene, antes de procesar la línea.
        current_check_level = indent_level
        if stripped_line.startswith(('}', 'else', 'case', 'default')):
            if current_check_level > 0:
                current_check_level -= 1
        
        expected_indent = current_check_level * 4
        leading_spaces = len(line) - len(line.lstrip(' '))

        # 1. Verificar si la indentación es un múltiplo de 4
        if leading_spaces % 4 != 0:
            errors.append((line_num, f"Regla 0xEEEEh: La indentación debe ser un múltiplo de 4 espacios. Se encontraron {leading_spaces}."))
        # 2. Verificar si la indentación es consistente con el nivel del bloque
        elif leading_spaces != expected_indent:
            errors.append((line_num, f"Regla 0xEEEEh: Indentación inconsistente. Se esperaba {expected_indent} espacios, pero se encontraron {leading_spaces}."))

        # Actualizar el nivel de indentación para la siguiente línea
        # Contar llaves que no estén en comentarios o cadenas
        line_for_braces = re.sub(r'//.*|/\*.*?\*/|"[^"]*"|\'[^\']*\'', '', line)
        open_braces = line_for_braces.count('{')
        close_braces = line_for_braces.count('}')
        indent_level += open_braces
        indent_level -= close_braces
        
        # Prevenir niveles de indentación negativos en caso de código malformado
        if indent_level < 0:
            indent_level = 0
            
    return errors

# --- Procesador de Archivos ---

def compile_file(filepath):
    """Compila un archivo C con GCC y devuelve la salida de errores y advertencias."""
    # Usar os.devnull para ser compatible con Windows y Linux/macOS
    output_binary = os.devnull 
    command = [
        'gcc', 
        '-Wall', 
        '-Wextra', 
        '-std=c23', 
        '-pedantic', 
        '-Wmissing-prototypes', 
        '-Wstrict-prototypes', 
        '-fanalyzer',
        filepath, 
        '-o', 
        output_binary
    ]
    try:
        # Ejecuta el comando de compilación
        result = subprocess.run(command, capture_output=True, text=True, timeout=15)
        # Los errores y advertencias de GCC se emiten en stderr, que es lo que devolvemos.
        return result.stderr
    except FileNotFoundError:
        return "Error: El compilador 'gcc' no se encontró en el PATH del sistema. No se pudo realizar la compilación."
    except subprocess.TimeoutExpired:
        return "Error: El proceso de compilación tardó demasiado (más de 15s) y fue terminado."
    except Exception as e:
        return f"Ocurrió un error inesperado durante la compilación: {e}"

def run_cppcheck(filepath):
    """Ejecuta Cppcheck en un archivo y devuelve la salida de errores."""
    command = [
        'cppcheck',
        '--enable=all',
        '--check-level=exhaustive',
        '--suppress=missingIncludeSystem',  # Suprime errores de headers no encontrados
        '--template=[{severity}] {file}:{line}: {id}: {message}',
        filepath
    ]
    try:
        # Cppcheck escribe sus resultados en stderr
        result = subprocess.run(command, capture_output=True, text=True, timeout=20)
        return result.stderr
    except FileNotFoundError:
        # Este caso es manejado por is_tool_installed, pero es una salvaguarda.
        return "Error: 'cppcheck' no encontrado."
    except subprocess.TimeoutExpired:
        return "Error: El análisis con Cppcheck tardó demasiado y fue terminado."
    except Exception as e:
        return f"Ocurrió un error inesperado al ejecutar Cppcheck: {e}"

def analyze_file(filepath):
    """Analiza un único archivo C y devuelve un diccionario con los resultados."""
    errors = []
    file_content = ""
    # --- MEJORA: Intentar leer el archivo con varias codificaciones comunes ---
    encodings_to_try = ['utf-8', 'latin-1', 'cp1252']
    
    for encoding in encodings_to_try:
        try:
            with open(filepath, 'r', encoding=encoding) as f:
                file_content = f.read()
            break # Si la lectura es exitosa, salimos del bucle
        except UnicodeDecodeError:
            continue # Si falla esta codificación, probamos la siguiente
        except Exception as e:
            # Para otros errores (ej. archivo no encontrado), reportamos y salimos
            msg = f"Error al leer el archivo: {e}"
            return {'errors': [(0, msg)], 'variables': [], 'io_functions': {}, 'functions_documentation': [], 'content': msg}

    # Si después de todos los intentos no se pudo leer el archivo
    if not file_content:
        msg = f"No se pudo decodificar el archivo con las codificaciones probadas: {', '.join(encodings_to_try)}"
        return {'errors': [(0, msg)], 'variables': [], 'io_functions': {}, 'functions_documentation': [], 'content': msg}

    lines = file_content.split('\n')
    
    # --- Ejecutar reglas que analizan el contenido completo ---
    variables_info = check_regla_0x0001(file_content)
    io_functions_info = check_regla_0x0009(file_content)
    functions_documentation_info = check_regla_0x000A(file_content)
    errors.extend(check_regla_0x0008(file_content))
    errors.extend(check_regla_0xEEEE(file_content)) # <- NUEVA REGLA DE INDENTACIÓN

    # --- Ejecutar reglas que analizan línea por línea ---
    in_function = False
    brace_level = 0
    for i, line in enumerate(lines):
        line_num = i + 1
        if '{' in line:
            brace_level += line.count('{')
            if brace_level > 0: in_function = True
        if '}' in line:
            brace_level -= line.count('}')
            if brace_level == 0: in_function = False

        errors.extend(check_regla_0x0000(line, line_num)) # <- NUEVA REGLA DE CLARIDAD
        errors.extend(check_regla_0x0002(line, line_num))
        errors.extend(check_regla_0x0004(line, line_num))
        errors.extend(check_regla_0x0005(line, line_num, lines))
        errors.extend(check_regla_0x0006(line, line_num))
        errors.extend(check_regla_0x000B(line, line_num, in_function))
        errors.extend(check_regla_0x000E(line, line_num))
        errors.extend(check_regla_0x0010(line, line_num))
        errors.extend(check_regla_0x0014(line, line_num))
        errors.extend(check_regla_0x0015(line, line_num))
        errors.extend(check_regla_0x0017(line, line_num))
        errors.extend(check_regla_0x0018(line, line_num))
        errors.extend(check_regla_0x001B(line, line_num))
        errors.extend(check_regla_0x001C(line, line_num))
        errors.extend(check_regla_0x002E(line, line_num))
        errors.extend(check_regla_0x0030h(line, line_num))
        
    return {
        'errors': errors, 
        'variables': variables_info, 
        'io_functions': io_functions_info,
        'functions_documentation': functions_documentation_info,
        'content': file_content
    }

def main():
    """Función principal del script."""
    if len(sys.argv) != 2:
        print("Uso: python verificar_estilo.py <ruta_al_directorio_base>")
        sys.exit(1)

    base_folder = sys.argv[1]
    if not os.path.isdir(base_folder):
        print(f"Error: La ruta '{base_folder}' no es una carpeta válida.")
        sys.exit(1)

    # --- Verificar herramientas una sola vez al inicio ---
    cppcheck_installed = is_tool_installed('cppcheck')
    if not cppcheck_installed:
        print("Advertencia: 'cppcheck' no está instalado o no se encuentra en el PATH. Se omitirá este análisis.")

    for student_dir_name in sorted(os.listdir(base_folder)):
        student_dir_path = os.path.join(base_folder, student_dir_name)
        if not os.path.isdir(student_dir_path):
            continue

        report_content = f"# Informe de Estilo para: {student_dir_name}\n\n"
        report_content += "\n\n**OBSERVACIÓN IMPORTANTE**\nEsto es una verificación automática de las reglas\n"
        c_files_to_analyze = []
        for root, _, files in os.walk(student_dir_path):
            for file in files:
                if file.endswith(".c"):
                    c_files_to_analyze.append(os.path.join(root, file))

        if not c_files_to_analyze:
            report_content += "No se encontraron archivos `.c` para analizar en este directorio.\n"
        
        for filepath in sorted(c_files_to_analyze):
            analysis = analyze_file(filepath)
            relative_filepath = os.path.relpath(filepath, student_dir_path)
            
            report_content += f"## Verificando: `{relative_filepath}`\n\n"
            report_content += "```c\n"
            report_content += analysis['content']
            report_content += "\n```\n\n"
            report_content += "### Estilo\n\n"

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
                         report_content += "\nTodos los identificadores _parecen_ se ven a simple vista, descriptivos.\n"
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
                            report_content += "**Comentario Encontrado:**\n\n"
                            comment_in_quote = "\n".join([f"{line}" for line in comment.split('\n')])
                            report_content += f"\n```c\n{comment_in_quote}\n{func_sig}\n```\n\n"
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
            
            # --- NUEVA SECCIÓN DE COMPILACIÓN ---
            report_content += "### Resultado de Compilación (GCC)\n\n"
            compilation_output = compile_file(filepath)
            if compilation_output.strip():
                report_content += "```text\n"
                report_content += compilation_output.strip()
                report_content += "\n```\n\n"
            else:
                report_content += "Compilación exitosa sin advertencias.\n\n"
            
            # --- NUEVA SECCIÓN DE ANÁLISIS CON CPPCHECK ---
            if cppcheck_installed:
                report_content += "### Análisis con Cppcheck\n\n"
                cppcheck_output = run_cppcheck(filepath)
                if cppcheck_output.strip():
                    report_content += "```text\n"
                    report_content += cppcheck_output.strip()
                    report_content += "\n```\n\n"
                else:
                    report_content += "Cppcheck no encontró problemas.\n\n"


        report_path = os.path.join(student_dir_path, f"{student_dir_name}.md")
        try:
            with open(report_path, "w", encoding="utf-8") as report_file:
                report_file.write(report_content)
            print(f"Análisis completado para '{student_dir_name}'. Informe guardado en: '{report_path}'")
        except IOError as e:
            print(f"Error al escribir el informe para '{student_dir_name}': {e}")

if __name__ == "__main__":
    main()

