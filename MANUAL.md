# Manual de Uso y Referencia Técnica: dredd

> **DREDD** — Multi-channel batch autograder and submission manager for C programming courses (GitHub Classroom & Moodle)
> **Versión:** `2.0.0` · **CLI principal:** `dredd` · **Plugin Ripley:** `dredd`

---

## 1. Arquitectura y Propósito Pedagógico

`dredd` forma parte del ecosistema de herramientas de la cátedra de Programación 1 (UNRN). Su objetivo central es resolver de forma modular, determinista y automatizada las tareas asociadas a su dominio específico dentro del ciclo de desarrollo, evaluación y aprendizaje de software en C.

### Alcance Funcional (Qué cubre)
- Orquestación central de corrección masiva de trabajos prácticos y exámenes de programación en C.
- Ingesta y normalización de entregas provenientes de Moodle (ZIPs) y GitHub Classroom (repositorios Git).
- Calificación ponderada y gestión de base de datos relacional SQLite (`dredd.db`).
- Detección de plagio y copias entre estudiantes mediante algoritmo de huellas digitales de Winnowing.
- Re-evaluación incremental rápida (`dredd rerun --failed-only` y `--dry-run`).
- Generación de reportes de devolución individual en Markdown y actas consolidadas.

### Límites de Responsabilidad y Delegación (Qué no cubre)
- Compilación directa y traducción pedagógica de errores (delega prioritariamente en `daedalus` y `esper`, con fallback a GCC).
- Ejecución aislada de binarios (delega en `nostromo` y Bubblewrap, con fallback por cuotas `setrlimit`).
- Linter de reglas de cátedra y estilo (delega en `gaff` y `ripley`, con fallback a linter nativo Tree-Sitter AST).
- Creación y multiplexación de guías de ejercicios (delega en `deckard`).

### Principios de Diseño
- **Enfoque Pedagógico:** Diagnósticos y mensajes en español rioplatense orientados a facilitar la comprensión de errores conceptuales.
- **Salida Estructurada Dual:** Soporte nativo para visualización enriquecida en terminal (Rich) y salida parseable para orquestadores (`--json`).
- **Integración Contractual:** Capacidad de emitir secciones de reporte para `dredd` (`dredd-section`) y actuar como satélite orquestado por `ripley`.
- **Idempotencia y Robustez:** Validación de precondiciones y comandos de autodiagnóstico (`doctor`) para verificación del entorno.

---

## 2. Instalación y Requisitos

### Requisitos del Sistema
- **Python:** `>= 3.10` (recomendado Python 3.11 o 3.12).
- **Gestor de paquetes:** [`uv`](https://github.com/astral-sh/uv) (entorno estándar de cátedra).
- **Toolchain C (si aplica):** GCC / Clang, Make, GDB y bibliotecas estándar de desarrollo.

### Instalación en el Entorno de Usuario
Para instalar la herramienta de forma global y aislada en el sistema mediante `uv tool`:
```bash
uv tool install --editable /home/mrtin/dev/tools/dredd
```

### Verificación de Instalación
Ejecutá el comando `doctor` para constatar que todas las dependencias y binarios requeridos estén presentes y operativos:
```bash
dredd doctor
```

---

## 3. Guía Integral de Comandos (CLI)

| Comando | Descripción Breve |
| :--- | :--- |
| [`dredd init`](#init) | Inicializa un espacio de trabajo de Dredd con carpetas estructuradas y mapeo declarativo en dredd.yaml. |
| [`dredd eval`](#eval) | Clona/actualiza el repositorio o evalúa entregas locales, ejecuta el análisis con Ripley y genera el informe Markdown. |
| [`dredd clean-eval`](#cleaneval) | Limpia las evaluaciones anteriores: elimina los directorios rNi y los informes generados. |
| [`dredd plagiarism`](#plagiarism) | Calcula la matriz de similitud Winnowing entre todas las entregas descargadas. |
| [`dredd map`](#map) | Mapeo interactivo y heurístico entre archivos C de estudiantes y especificaciones de la guía. |
| [`dredd export`](#export) | Exporta calificaciones CSV, paquete ZIP de retroalimentación y dashboard consolidado de cohorte. |
| [`dredd export-report`](#exportreport) | Convierte un informe Markdown a HTML autocontenido enriquecido o PDF (zero-dependencies). |
| [`dredd fuzz-gen`](#fuzzgen) | fuzz-gen: endurece el banco generando casos límite contra la solución modelo. |
| [`dredd oral-guide`](#oralguide) | oral-exam-companion: genera una guía de preguntas para coloquio/defensa. |
| [`dredd multiplex`](#multiplex) | Alias docente de conveniencia que delega la generación de variantes y asignación en Deckard. |
| [`dredd doctor`](#doctor) | Verifica dependencias externas del sistema (GCC, Valgrind, Bubblewrap, Git, Ripley). |
| [`dredd rerun`](#rerun) | Re-ejecuta la evaluación sobre entregas desaprobadas o con observaciones críticas. |
| [`dredd export-guarani`](#exportguarani) | Exporta las calificaciones finales en formato estándar de actas de SIU Guaraní. |
| [`dredd serve-dashboard`](#servedashboard) | Inicia un servidor web local para visualizar el dashboard de notas y plagio. |
| [`dredd dashboard`](#dashboard) | Inicia un servidor web local para visualizar el dashboard de notas y plagio. |
| [`dredd audit-git`](#auditgit) | Audita anomalías temporales y patrones de desarrollo en commits de Git. |
| [`dredd git-forensics`](#gitforensics) | Audita marcas de tiempo en Git para detectar alteraciones manuales o rebase masivo previo a entrega. |
| [`dredd notify-batch`](#notifybatch) | Empaqueta y exporta los informes individuales alumno_rN.md en un lote consolidado con ZIP. |
| [`dredd export-feedback`](#exportfeedback) | Empaqueta y exporta los informes individuales alumno_rN.md en un lote consolidado con ZIP. |
| [`dredd plagiarism-historical`](#plagiarismhistorical) | Detecta plagio cruzado inter-anual contra entregas históricas. |
| [`dredd diff-revision`](#diffrevision) | Compara dos versiones sucesivas de una entrega (R1 vs R2) mostrando cambios en código y funciones (QoL 3.15). |
| [`dredd diff-submission`](#diffsubmission) | Compara dos versiones sucesivas de una entrega (R1 vs R2) mostrando cambios en código y funciones (QoL 3.15). |
| [`dredd late-penalty`](#latepenalty) | Calcula la penalización gradual por entrega fuera de término. |
| [`dredd audit-makefile`](#auditmakefile) | Audita Makefiles en busca de dependencias prohibidas, flags suprimidas y trampas. |
| [`dredd typology`](#typology) | Clasifica automáticamente la tipología arquitectónica de una entrega (monolítica, modular, librería, incompleta). |
| [`dredd eval-stability`](#evalstability) | Evalúa la estabilidad temporal y determinismo de una solución mediante corridas reiteradas. |
| [`dredd cohort-bench`](#cohortbench) | Ejecuta benchmarking algorítmico comparativo de CPU y memoria en toda la cohorte. |
| [`dredd smith-adversary`](#smithadversary) | Genera e inyecta casos de prueba adversarios y de estrés (integración smith). |
| [`dredd eval-shielded`](#evalshielded) | Ejecuta un proceso bajo el modo 'Sandbox Blindado' con corte total de red y namespaces aislados. |
| [`dredd report-template`](#reporttemplate) | Renderiza o valida plantillas de feedback Markdown enriquecidas con variables contextuales. |
| [`dredd sanitize-output`](#sanitizeoutput) | Sanitiza flujos de salida o logs estudiantiles eliminando secuencias ANSI y truncando si excede el límite. |

### `dredd init`

Inicializa un espacio de trabajo de Dredd con carpetas estructuradas y mapeo declarativo en dredd.yaml.

#### Opciones y Banderas
| Opción / Banderas | Tipo | Por Defecto | Descripción |
| :--- | :--- | :--- | :--- |
| `--path` | `<class 'pathlib._local.Path'>` | `.` | Directorio raíz donde inicializar el workspace de Dredd. |
| `--name`, `-n` | `<class 'str'>` | `Cátedra Programación 1` | Nombre del espacio de trabajo o materia. |
| `--zips`, `-z` | `<class 'str'>` | `zips` | Directorio para almacenar los archivos ZIP de Moodle. |
| `--entregas`, `-e` | `<class 'str'>` | `entregas` | Directorio para las entregas descompactadas. |
| `--guias`, `-g` | `<class 'str'>` | `guias` | Directorio para las guías de Deckard. |
| `--force`, `-f` | `<class 'bool'>` | `False` | Sobrescribir dredd.yaml si ya existe. |

#### Ejemplo de Invocación
```bash
dredd init
```

### `dredd eval`

Clona/actualiza el repositorio o evalúa entregas locales, ejecuta el análisis con Ripley y genera el informe Markdown.

#### Argumentos
| Argumento | Tipo | Descripción |
| :--- | :--- | :--- |
| `exercise` | `<class 'str'>` | Nombre de la actividad / ejercicio o ruta al directorio de entregas (ej. tp01, ./entrega-3_1238305/). |

#### Opciones y Banderas
| Opción / Banderas | Tipo | Por Defecto | Descripción |
| :--- | :--- | :--- | :--- |
| `--student` | `Optional[str]` | `None` | Nombre de usuario del estudiante (opcional si se usa --all). |
| `--org`, `-o` | `<class 'str'>` | `INGCOM-UNRN-P1` | Organización de GitHub. |
| `--all`, `-a` | `<class 'bool'>` | `False` | Evaluar todos los estudiantes presentes en el workspace. |
| `--template-dir`, `-t` | `<class 'pathlib._local.Path'>` | `informe` | Directorio con header.md y footer.md. |
| `--tipo-entrega`, `--build-mode`, `-m` | `Optional[str]` | `None` | Tipo de entrega / modo de construcción ('archivos_individuales', 'makefiles_individuales' o 'proyecto'). Hace override a dredd.yaml y Deckard. |
| `--dry-run` | `<class 'bool'>` | `False` | Modo Dry Run: evalúa únicamente una muestra de hasta 3 estudiantes representativos antes del lote completo. |
| `--baseline`, `-b` | `Optional[pathlib._local.Path]` | `None` | Directorio de línea base (_baseline) con las plantillas originales para omitir ejercicios sin completar. |
| `--clean`, `-c` | `<class 'bool'>` | `False` | Limpia directorios de evaluación (rNi) e informes previos antes de volver a evaluar. |
| `--force`, `-f` | `<class 'bool'>` | `False` | Fuerza la re-evaluación completa eliminando resultados previos de las carpetas de estudiantes. |
| `--json` | `<class 'bool'>` | `False` | Emite el resultado estructurado de la evaluación en formato JSON (máquina a máquina). |
| `--workspace`, `-w` | `<class 'pathlib._local.Path'>` | `.` | Directorio raíz del workspace. |

#### Ejemplo de Invocación
```bash
dredd eval <exercise>
```

### `dredd clean-eval`

Limpia las evaluaciones anteriores: elimina los directorios rNi y los informes generados.

#### Opciones y Banderas
| Opción / Banderas | Tipo | Por Defecto | Descripción |
| :--- | :--- | :--- | :--- |
| `--exercise` | `Optional[str]` | `None` | Nombre de la actividad o ruta al directorio de entregas (ej. tp01, ./entregas). Si no se indica, limpia en ./entregas o en el directorio actual. |
| `--student` | `Optional[str]` | `None` | Nombre de usuario del estudiante específico a limpiar (opcional; por defecto limpia todos). |
| `--all`, `-a` | `<class 'bool'>` | `False` | Limpiar todas las entregas encontradas. |
| `--dry-run`, `-n` | `<class 'bool'>` | `False` | Modo simulación: muestra qué carpetas rNi e informes se eliminarían sin borrar archivos. |
| `--rni-only` | `<class 'bool'>` | `False` | Limpiar exclusivamente los directorios rNi de herramientas, conservando los informes consolidados. |
| `--reports-only` | `<class 'bool'>` | `False` | Limpiar exclusivamente los archivos de informes Markdown/HTML/PDF, conservando los directorios rNi. |
| `--verbose`, `-v` | `<class 'bool'>` | `False` | Muestra cada archivo y carpeta eliminado en consola. |

#### Ejemplo de Invocación
```bash
dredd clean-eval
```

### `dredd plagiarism`

Calcula la matriz de similitud Winnowing entre todas las entregas descargadas.

#### Argumentos
| Argumento | Tipo | Descripción |
| :--- | :--- | :--- |
| `exercise` | `<class 'str'>` | Nombre de la actividad o directorio de entregas a auditar. |

#### Opciones y Banderas
| Opción / Banderas | Tipo | Por Defecto | Descripción |
| :--- | :--- | :--- | :--- |
| `--threshold`, `-th` | `<class 'float'>` | `0.6` | Umbral de similitud mínima (0.0 a 1.0). |
| `--strip-template` | `Optional[pathlib._local.Path]` | `None` | boiler-strip: plantilla/archivo(s) de cátedra a eliminar antes de calcular similitud. |
| `--html` | `Optional[pathlib._local.Path]` | `None` | Ruta del reporte HTML interactivo con matriz y diff lado a lado. |

#### Ejemplo de Invocación
```bash
dredd plagiarism <exercise>
```

### `dredd map`

Mapeo interactivo y heurístico entre archivos C de estudiantes y especificaciones de la guía.

#### Argumentos
| Argumento | Tipo | Descripción |
| :--- | :--- | :--- |
| `activity` | `<class 'str'>` | Nombre / slug de la actividad o directorio de entregas a mapear (ej. tp01, ./entrega-3_1238305/). |

#### Opciones y Banderas
| Opción / Banderas | Tipo | Por Defecto | Descripción |
| :--- | :--- | :--- | :--- |
| `--exercise`, `-e` | `Optional[List[str]]` | `None` | Nombres de los ejercicios disponibles (ej. -e ej1 -e ej2). |
| `--unmapped-only`, `-u` | `<class 'bool'>` | `False` | Revisar únicamente archivos no vinculados. |
| `--auto`, `-a` | `<class 'bool'>` | `False` | Aplicar coincidencias heurísticas obvias automáticamente. |

#### Ejemplo de Invocación
```bash
dredd map <activity>
```

### `dredd export`

Exporta calificaciones CSV, paquete ZIP de retroalimentación y dashboard consolidado de cohorte.

#### Argumentos
| Argumento | Tipo | Descripción |
| :--- | :--- | :--- |
| `activity` | `<class 'str'>` | Nombre / slug de la actividad a exportar. |

#### Opciones y Banderas
| Opción / Banderas | Tipo | Por Defecto | Descripción |
| :--- | :--- | :--- | :--- |
| `--csv`, `-c` | `Optional[pathlib._local.Path]` | `None` | Ruta del CSV de calificaciones Moodle. |
| `--zip`, `-z` | `Optional[pathlib._local.Path]` | `None` | Ruta del ZIP de retroalimentación Moodle. |
| `--dashboard`, `-d` | `Optional[pathlib._local.Path]` | `None` | Ruta del dashboard Markdown. |

#### Ejemplo de Invocación
```bash
dredd export <activity>
```

### `dredd export-report`

Convierte un informe Markdown a HTML autocontenido enriquecido o PDF (zero-dependencies).

#### Argumentos
| Argumento | Tipo | Descripción |
| :--- | :--- | :--- |
| `source` | `<class 'pathlib._local.Path'>` | Ruta al archivo Markdown (.md) del informe. |

#### Opciones y Banderas
| Opción / Banderas | Tipo | Por Defecto | Descripción |
| :--- | :--- | :--- | :--- |
| `--format`, `-f` | `<class 'str'>` | `html` | Formato de exportación: 'html' o 'pdf'. |
| `--output`, `-o` | `Optional[pathlib._local.Path]` | `None` | Ruta del archivo de salida. |
| `--title`, `-t` | `<class 'str'>` | `Informe de Evaluación — Dredd` | Título del informe. |

#### Ejemplo de Invocación
```bash
dredd export-report <source>
```

### `dredd fuzz-gen`

fuzz-gen: endurece el banco generando casos límite contra la solución modelo.

Combina semillas extremas deterministas (INT_MAX/INT_MIN, cadenas vacías,
tamaños 0..N) con mutaciones y —si clang+libFuzzer están disponibles—
fuzzing guiado por cobertura. Cada candidato se ejecuta contra el modelo
para fijar la salida esperada; duplicados y crashes se reportan aparte.

#### Argumentos
| Argumento | Tipo | Descripción |
| :--- | :--- | :--- |
| `modelo` | `<class 'pathlib._local.Path'>` | Solución modelo de la cátedra (.c). |

#### Opciones y Banderas
| Opción / Banderas | Tipo | Por Defecto | Descripción |
| :--- | :--- | :--- | :--- |
| `--salida`, `-o` | `<class 'pathlib._local.Path'>` | `casos` | Directorio destino de los pares caso_NN.in/.out. |
| `--spec` | `Optional[pathlib._local.Path]` | `None` | spec.yaml opcional (tipo_entrada, semillas_extra, tamano_max). |
| `--cantidad`, `-n` | `<class 'int'>` | `12` | Máximo de testcases a generar. |
| `--segundos` | `<class 'int'>` | `15` | Tiempo de fuzzing si hay clang/libFuzzer. |
| `--sin-libfuzzer` | `<class 'bool'>` | `False` | Fuerza el modo determinista. |

#### Ejemplo de Invocación
```bash
dredd fuzz-gen <modelo>
```

### `dredd oral-guide`

oral-exam-companion: genera una guía de preguntas para coloquio/defensa.

#### Argumentos
| Argumento | Tipo | Descripción |
| :--- | :--- | :--- |
| `repo` | `<class 'pathlib._local.Path'>` | Repositorio del alumno (clonado en el workspace). |

#### Opciones y Banderas
| Opción / Banderas | Tipo | Por Defecto | Descripción |
| :--- | :--- | :--- | :--- |
| `--alumno` | `Optional[str]` | `None` | Nombre legible del alumno. |
| `--ejercicio` | `Optional[str]` | `None` | TP/parcial asociado. |
| `-o`, `--salida` | `Optional[pathlib._local.Path]` | `None` | Archivo .md destino (por defecto, stdout). |
| `--sin-ripley` | `<class 'bool'>` | `False` | No correr análisis técnico. |

#### Ejemplo de Invocación
```bash
dredd oral-guide <repo>
```

### `dredd multiplex`

Alias docente de conveniencia que delega la generación de variantes y asignación en Deckard.

#### Argumentos
| Argumento | Tipo | Descripción |
| :--- | :--- | :--- |
| `spec` | `<class 'pathlib._local.Path'>` | Ruta al archivo matriz.yaml. |

#### Opciones y Banderas
| Opción / Banderas | Tipo | Por Defecto | Descripción |
| :--- | :--- | :--- | :--- |
| `--students` | `Optional[pathlib._local.Path]` | `None` | CSV con lista de alumnos. |
| `--salida`, `-o` | `<class 'pathlib._local.Path'>` | `dist/multiplex` | Directorio destino de la multiplexación. |
| `--pack/--no-pack` | `<class 'bool'>` | `True` | Generar paquetes .ripkg para cada variante. |
| `--starters/--no-starters` | `<class 'bool'>` | `True` | Generar starter repos por alumno. |

#### Ejemplo de Invocación
```bash
dredd multiplex <spec>
```

### `dredd doctor`

Verifica dependencias externas del sistema (GCC, Valgrind, Bubblewrap, Git, Ripley).

#### Ejemplo de Invocación
```bash
dredd doctor
```

### `dredd rerun`

Re-ejecuta la evaluación sobre entregas desaprobadas o con observaciones críticas.

#### Argumentos
| Argumento | Tipo | Descripción |
| :--- | :--- | :--- |
| `exercise` | `<class 'str'>` | Nombre de la actividad / ejercicio a re-evaluar. |

#### Opciones y Banderas
| Opción / Banderas | Tipo | Por Defecto | Descripción |
| :--- | :--- | :--- | :--- |
| `--student` | `Optional[str]` | `None` | Nombre de usuario del estudiante específico a re-evaluar (opcional). |
| `--failed-only/--all-rerun` | `<class 'bool'>` | `True` | Re-evaluar únicamente entregas desaprobadas o con fallos de compilación. |
| `--tipo-entrega`, `--build-mode`, `-m` | `Optional[str]` | `None` | Tipo de entrega / modo de construcción ('archivos_individuales', 'makefiles_individuales' o 'proyecto'). |
| `--dry-run` | `<class 'bool'>` | `False` | Modo Dry Run: evalúa únicamente una muestra de hasta 3 estudiantes representativos. |
| `--workspace`, `-w` | `<class 'pathlib._local.Path'>` | `.` | Directorio raíz del workspace. |

#### Ejemplo de Invocación
```bash
dredd rerun <exercise>
```

### `dredd export-guarani`

Exporta las calificaciones finales en formato estándar de actas de SIU Guaraní.

#### Opciones y Banderas
| Opción / Banderas | Tipo | Por Defecto | Descripción |
| :--- | :--- | :--- | :--- |
| `--entregas` | `<class 'pathlib._local.Path'>` | `entregas` | Directorio de entregas o base de datos de calificaciones. |
| `--output`, `-o` | `<class 'pathlib._local.Path'>` | `acta_guarani.csv` | Ruta de destino del CSV de SIU Guaraní. |

#### Ejemplo de Invocación
```bash
dredd export-guarani
```

### `dredd serve-dashboard`

Inicia un servidor web local para visualizar el dashboard de notas y plagio.

#### Opciones y Banderas
| Opción / Banderas | Tipo | Por Defecto | Descripción |
| :--- | :--- | :--- | :--- |
| `--port`, `-p` | `<class 'int'>` | `8000` | Puerto HTTP para el servidor de dashboard local. |
| `--host`, `-H` | `<class 'str'>` | `127.0.0.1` | Dirección IP o host local de escucha. |
| `--entregas`, `-e` | `<class 'pathlib._local.Path'>` | `entregas` | Directorio con las entregas de los estudiantes para extraer notas. |
| `--data`, `-d` | `Optional[pathlib._local.Path]` | `None` | Ruta a un archivo JSON con métricas precalculadas. |
| `--verbose`, `-v` | `<class 'bool'>` | `False` | Muestra información detallada de diagnóstico y registro de peticiones HTTP en consola. |

#### Ejemplo de Invocación
```bash
dredd serve-dashboard
```

### `dredd dashboard`

Inicia un servidor web local para visualizar el dashboard de notas y plagio.

#### Opciones y Banderas
| Opción / Banderas | Tipo | Por Defecto | Descripción |
| :--- | :--- | :--- | :--- |
| `--port`, `-p` | `<class 'int'>` | `8000` | Puerto HTTP para el servidor de dashboard local. |
| `--host`, `-H` | `<class 'str'>` | `127.0.0.1` | Dirección IP o host local de escucha. |
| `--entregas`, `-e` | `<class 'pathlib._local.Path'>` | `entregas` | Directorio con las entregas de los estudiantes para extraer notas. |
| `--data`, `-d` | `Optional[pathlib._local.Path]` | `None` | Ruta a un archivo JSON con métricas precalculadas. |
| `--verbose`, `-v` | `<class 'bool'>` | `False` | Muestra información detallada de diagnóstico y registro de peticiones HTTP en consola. |

#### Ejemplo de Invocación
```bash
dredd dashboard
```

### `dredd audit-git`

Audita anomalías temporales y patrones de desarrollo en commits de Git.

#### Opciones y Banderas
| Opción / Banderas | Tipo | Por Defecto | Descripción |
| :--- | :--- | :--- | :--- |
| `--repo` | `<class 'pathlib._local.Path'>` | `.` | Ruta al repositorio de la entrega a auditar. |

#### Ejemplo de Invocación
```bash
dredd audit-git
```

### `dredd git-forensics`

Audita marcas de tiempo en Git para detectar alteraciones manuales o rebase masivo previo a entrega.

#### Opciones y Banderas
| Opción / Banderas | Tipo | Por Defecto | Descripción |
| :--- | :--- | :--- | :--- |
| `--repo` | `<class 'pathlib._local.Path'>` | `.` | Ruta al repositorio de la entrega a auditar. |
| `--max-skew` | `<class 'int'>` | `300` | Tolerancia en segundos para desfase entre autor y committer. |
| `--json` | `<class 'bool'>` | `False` | Exporta el resultado en formato JSON estándar. |
| `--fail-on-anomaly` | `<class 'bool'>` | `False` | Finaliza con código de error si el riesgo forense es ALTO. |

#### Ejemplo de Invocación
```bash
dredd git-forensics
```

### `dredd notify-batch`

Empaqueta y exporta los informes individuales alumno_rN.md en un lote consolidado con ZIP.

#### Opciones y Banderas
| Opción / Banderas | Tipo | Por Defecto | Descripción |
| :--- | :--- | :--- | :--- |
| `--entregas` | `<class 'pathlib._local.Path'>` | `entregas` | Directorio con las entregas de los estudiantes. |
| `--output`, `-o` | `<class 'pathlib._local.Path'>` | `feedbacks_lote` | Directorio de destino para los reportes. |

#### Ejemplo de Invocación
```bash
dredd notify-batch
```

### `dredd export-feedback`

Empaqueta y exporta los informes individuales alumno_rN.md en un lote consolidado con ZIP.

#### Opciones y Banderas
| Opción / Banderas | Tipo | Por Defecto | Descripción |
| :--- | :--- | :--- | :--- |
| `--entregas` | `<class 'pathlib._local.Path'>` | `entregas` | Directorio con las entregas de los estudiantes. |
| `--output`, `-o` | `<class 'pathlib._local.Path'>` | `feedbacks_lote` | Directorio de destino para los reportes. |

#### Ejemplo de Invocación
```bash
dredd export-feedback
```

### `dredd plagiarism-historical`

Detecta plagio cruzado inter-anual contra entregas históricas.

#### Argumentos
| Argumento | Tipo | Descripción |
| :--- | :--- | :--- |
| `dir_actual` | `<class 'pathlib._local.Path'>` | Directorio de entregas del cuatrimestre actual. |
| `dir_historico` | `<class 'pathlib._local.Path'>` | Directorio de entregas históricas de años previos. |

#### Opciones y Banderas
| Opción / Banderas | Tipo | Por Defecto | Descripción |
| :--- | :--- | :--- | :--- |
| `--threshold`, `-t` | `<class 'float'>` | `0.7` | Umbral de similitud mínima para alertar plagio. |

#### Ejemplo de Invocación
```bash
dredd plagiarism-historical <dir_actual> <dir_historico>
```

### `dredd diff-revision`

Compara dos versiones sucesivas de una entrega (R1 vs R2) mostrando cambios en código y funciones (QoL 3.15).

#### Argumentos
| Argumento | Tipo | Descripción |
| :--- | :--- | :--- |
| `objetivo` | `<class 'str'>` | Ruta al directorio de la entrega o ruta a la primera versión R1. |

#### Opciones y Banderas
| Opción / Banderas | Tipo | Por Defecto | Descripción |
| :--- | :--- | :--- | :--- |
| `--segunda-version` | `Optional[str]` | `None` | Ruta a la segunda versión R2 o nombre de revisión (ej. 'r2'). |
| `--r1` | `Optional[str]` | `None` | Nombre o subcarpeta de la primera revisión. |
| `--r2` | `Optional[str]` | `None` | Nombre o subcarpeta de la segunda revisión. |
| `--entregas`, `-e` | `<class 'pathlib._local.Path'>` | `entregas` | Directorio base de entregas si se pasa nombre de alumno. |
| `--json` | `<class 'bool'>` | `False` | Emitir reporte de diff en formato JSON. |
| `--md`, `--output-md`, `-o` | `Optional[pathlib._local.Path]` | `None` | Exportar reporte de diff a archivo Markdown. |

#### Ejemplo de Invocación
```bash
dredd diff-revision <objetivo>
```

### `dredd diff-submission`

Compara dos versiones sucesivas de una entrega (R1 vs R2) mostrando cambios en código y funciones (QoL 3.15).

#### Argumentos
| Argumento | Tipo | Descripción |
| :--- | :--- | :--- |
| `objetivo` | `<class 'str'>` | Ruta al directorio de la entrega o ruta a la primera versión R1. |

#### Opciones y Banderas
| Opción / Banderas | Tipo | Por Defecto | Descripción |
| :--- | :--- | :--- | :--- |
| `--segunda-version` | `Optional[str]` | `None` | Ruta a la segunda versión R2 o nombre de revisión (ej. 'r2'). |
| `--r1` | `Optional[str]` | `None` | Nombre o subcarpeta de la primera revisión. |
| `--r2` | `Optional[str]` | `None` | Nombre o subcarpeta de la segunda revisión. |
| `--entregas`, `-e` | `<class 'pathlib._local.Path'>` | `entregas` | Directorio base de entregas si se pasa nombre de alumno. |
| `--json` | `<class 'bool'>` | `False` | Emitir reporte de diff en formato JSON. |
| `--md`, `--output-md`, `-o` | `Optional[pathlib._local.Path]` | `None` | Exportar reporte de diff a archivo Markdown. |

#### Ejemplo de Invocación
```bash
dredd diff-submission <objetivo>
```

### `dredd late-penalty`

Calcula la penalización gradual por entrega fuera de término.

#### Argumentos
| Argumento | Tipo | Descripción |
| :--- | :--- | :--- |
| `fecha_entrega` | `<class 'str'>` | Fecha y hora de entrega (ISO o 'YYYY-MM-DD HH:MM'). |
| `fecha_limite` | `<class 'str'>` | Fecha y hora límite de entrega (ISO o 'YYYY-MM-DD HH:MM'). |

#### Opciones y Banderas
| Opción / Banderas | Tipo | Por Defecto | Descripción |
| :--- | :--- | :--- | :--- |
| `--nota`, `-n` | `<class 'float'>` | `10.0` | Calificación base antes de la penalización. |
| `--gracia`, `-g` | `<class 'int'>` | `15` | Minutos de gracia sin penalización. |
| `--tasa`, `-t` | `<class 'float'>` | `0.25` | Puntos de descuento por cada hora de retraso. |
| `--max-descuento`, `-m` | `<class 'float'>` | `4.0` | Tope máximo de puntos de descuento. |
| `--json` | `<class 'bool'>` | `False` | Emitir resultado en formato JSON. |

#### Ejemplo de Invocación
```bash
dredd late-penalty <fecha_entrega> <fecha_limite>
```

### `dredd audit-makefile`

Audita Makefiles en busca de dependencias prohibidas, flags suprimidas y trampas.

#### Argumentos
| Argumento | Tipo | Descripción |
| :--- | :--- | :--- |
| `objetivo` | `<class 'pathlib._local.Path'>` | Ruta al archivo Makefile o al directorio de la entrega. |

#### Opciones y Banderas
| Opción / Banderas | Tipo | Por Defecto | Descripción |
| :--- | :--- | :--- | :--- |
| `--json` | `<class 'bool'>` | `False` | Salida en formato JSON. |

#### Ejemplo de Invocación
```bash
dredd audit-makefile <objetivo>
```

### `dredd typology`

Clasifica automáticamente la tipología arquitectónica de una entrega (monolítica, modular, librería, incompleta).

#### Argumentos
| Argumento | Tipo | Descripción |
| :--- | :--- | :--- |
| `directorio` | `<class 'pathlib._local.Path'>` | Directorio de la entrega del alumno o carpeta de entregas. |

#### Opciones y Banderas
| Opción / Banderas | Tipo | Por Defecto | Descripción |
| :--- | :--- | :--- | :--- |
| `--json` | `<class 'bool'>` | `False` | Salida en formato JSON. |

#### Ejemplo de Invocación
```bash
dredd typology <directorio>
```

### `dredd eval-stability`

Evalúa la estabilidad temporal y determinismo de una solución mediante corridas reiteradas.

#### Argumentos
| Argumento | Tipo | Descripción |
| :--- | :--- | :--- |
| `binario` | `<class 'pathlib._local.Path'>` | Ruta al binario ejecutable C. |

#### Opciones y Banderas
| Opción / Banderas | Tipo | Por Defecto | Descripción |
| :--- | :--- | :--- | :--- |
| `--repeticiones`, `-n` | `<class 'int'>` | `5` | Número de ejecuciones consecutivas. |
| `--input`, `-i` | `<class 'str'>` | `` | Datos de entrada stdin para el proceso. |
| `--timeout`, `-t` | `<class 'float'>` | `3.0` | Timeout por corrida en segundos. |
| `--json` | `<class 'bool'>` | `False` | Salida en formato JSON. |

#### Ejemplo de Invocación
```bash
dredd eval-stability <binario>
```

### `dredd cohort-bench`

Ejecuta benchmarking algorítmico comparativo de CPU y memoria en toda la cohorte.

#### Argumentos
| Argumento | Tipo | Descripción |
| :--- | :--- | :--- |
| `entregas` | `<class 'pathlib._local.Path'>` | Directorio contenedor de las entregas de la cohorte. |

#### Opciones y Banderas
| Opción / Banderas | Tipo | Por Defecto | Descripción |
| :--- | :--- | :--- | :--- |
| `--bin`, `-b` | `<class 'str'>` | `main` | Nombre del archivo binario ejecutable a comparar. |
| `--input`, `-i` | `<class 'str'>` | `` | Datos de entrada para el benchmark. |
| `--timeout`, `-t` | `<class 'float'>` | `5.0` | Timeout máximo por entrega en segundos. |
| `--json` | `<class 'bool'>` | `False` | Salida en formato JSON. |

#### Ejemplo de Invocación
```bash
dredd cohort-bench <entregas>
```

### `dredd smith-adversary`

Genera e inyecta casos de prueba adversarios y de estrés (integración smith).

#### Argumentos
| Argumento | Tipo | Descripción |
| :--- | :--- | :--- |
| `target` | `<class 'pathlib._local.Path'>` | Ruta a binario ejecutable o directorio de tests para inyección. |

#### Opciones y Banderas
| Opción / Banderas | Tipo | Por Defecto | Descripción |
| :--- | :--- | :--- | :--- |
| `--inject` | `<class 'bool'>` | `False` | Inyectar casos adversarios .in en la carpeta destino. |
| `--timeout`, `-t` | `<class 'float'>` | `2.0` | Timeout por caso adversario en segundos. |
| `--json` | `<class 'bool'>` | `False` | Salida en formato JSON. |

#### Ejemplo de Invocación
```bash
dredd smith-adversary <target>
```

### `dredd eval-shielded`

Ejecuta un proceso bajo el modo 'Sandbox Blindado' con corte total de red y namespaces aislados.

#### Argumentos
| Argumento | Tipo | Descripción |
| :--- | :--- | :--- |
| `cmd` | `<class 'str'>` | Comando binario a ejecutar en sandbox blindado. |

#### Opciones y Banderas
| Opción / Banderas | Tipo | Por Defecto | Descripción |
| :--- | :--- | :--- | :--- |
| `--input`, `-i` | `<class 'str'>` | `` | Entrada stdin. |
| `--timeout`, `-t` | `<class 'float'>` | `3.0` | Timeout máximo en segundos. |
| `--memory`, `-m` | `<class 'int'>` | `48` | Límite estricto de memoria en MB. |

#### Ejemplo de Invocación
```bash
dredd eval-shielded <cmd>
```

### `dredd report-template`

Renderiza o valida plantillas de feedback Markdown enriquecidas con variables contextuales.

#### Opciones y Banderas
| Opción / Banderas | Tipo | Por Defecto | Descripción |
| :--- | :--- | :--- | :--- |
| `--template`, `-t` | `Optional[pathlib._local.Path]` | `None` | Ruta a la plantilla Markdown con variables contextuales. |
| `--student`, `-s` | `<class 'str'>` | `estudiante_ejemplo` | Identificador o nombre del estudiante. |
| `--exercise`, `-e` | `<class 'str'>` | `guia_c` | Nombre del ejercicio o TP. |
| `--score` | `<class 'str'>` | `9.0` | Calificación para la previsualización. |
| `--total-tests` | `<class 'int'>` | `10` | Total de casos de prueba. |
| `--passed-tests` | `<class 'int'>` | `9` | Casos de prueba aprobados. |
| `--failures` | `<class 'str'>` | `Caso límite 02: retorno inesperado` | Descripción o detalle de fallos. |
| `--memory-summary` | `<class 'str'>` | `✓ Sin fugas de memoria (0 bytes perdidos)` | Resumen de memoria dinámica. |
| `--badge` | `<class 'str'>` | `✅ **ENTREGA APROBADA**` | Insignia de estado general. |
| `--output`, `-o` | `Optional[pathlib._local.Path]` | `None` | Guardar el reporte renderizado en un archivo. |
| `--dump-default` | `<class 'bool'>` | `False` | Imprimir o guardar la plantilla por defecto sin renderizar. |

#### Ejemplo de Invocación
```bash
dredd report-template
```

### `dredd sanitize-output`

Sanitiza flujos de salida o logs estudiantiles eliminando secuencias ANSI y truncando si excede el límite.

#### Argumentos
| Argumento | Tipo | Descripción |
| :--- | :--- | :--- |
| `file` | `<class 'pathlib._local.Path'>` | Archivo de log o volcado de salida a sanitizar. |

#### Opciones y Banderas
| Opción / Banderas | Tipo | Por Defecto | Descripción |
| :--- | :--- | :--- | :--- |
| `--max-mb` | `<class 'int'>` | `10` | Límite máximo seguro en megabytes antes de truncar. |
| `--output`, `-o` | `Optional[pathlib._local.Path]` | `None` | Archivo de destino (por defecto sobrescribe el original). |
| `--no-strip-ansi` | `<class 'bool'>` | `False` | No remover secuencias de escape ANSI. |

#### Ejemplo de Invocación
```bash
dredd sanitize-output <file>
```

---

## 4. Formatos de Salida e Integración con el Ecosistema

### Modo Interactivo / Terminal (Rich)
Por defecto, la herramienta renderiza paneles, árboles y tablas estilizadas para facilitar la lectura del estudiante y docente en terminales modernas con soporte ANSI.

### Modo Estructurado JSON (`--json`)
Para integración con pipelines de CI/CD, scripts de automatización u orquestadores externos, la opción `--json` emite un documento JSON estricto por la salida estándar (`stdout`), dirigiendo cualquier mensaje de logging a `stderr`:
```bash
dredd init --json
```

### Integración con Dredd (`dredd-section`)
Cuando la herramienta genera reportes de evaluación para entregas de alumnos, produce una sección Markdown estandarizada conforme al contrato de integración de Dredd (v1.0.0):
```markdown
<!-- dredd-section: dredd, tool=dredd, version=2.0.0, status=ok -->
```
Este encabezado garantiza la agregación determinista de los hallazgos en la rúbrica docente.

### Integración con Ripley
`dredd` está registrada en el catálogo de plugins satélites de Ripley (`SATELLITE_CATALOG`). Puede invocarse directamente a través del motor de evaluación de Ripley configurando el análisis en `ripley.toml`.

---

## 5. Diagnóstico y Códigos de Salida

### Códigos de Retorno (`exit code`)
| Código | Significado |
| :---: | :--- |
| `0` | Ejecución exitosa sin hallazgos críticos ni errores de sintaxis. |
| `1` | Hallazgos pedagógicos detectados, infracción de reglas o advertencias activas. |
| `2` | Error de sintaxis en argumentos CLI o archivo fuente no encontrado. |
| `>2` | Error no recuperable del sistema, fallo de memoria o excepción interna. |

### Diagnóstico del Entorno (`doctor`)
Ante comportamientos inesperados, verificá el estado operativo con:
```bash
dredd doctor
```
Comprueba la presencia de las dependencias requeridas y la integridad de los componentes del paquete.