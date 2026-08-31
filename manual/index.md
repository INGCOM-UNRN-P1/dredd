---
title: "Manual de Referencia: dredd"
subtitle: "Dredd — Orquestador Docente de Evaluación Masiva, Autograding y Detección de Plagio Winnowing"
author: "Cátedra de Algoritmos y Programación"
date: "2026-08-31"
---

(manual-dredd)=
# Dredd — Orquestador Docente de Evaluación Masiva, Autograding y Detección de Plagio Winnowing

````{abstract}
**Rol en el ecosistema:** Orquestación batch de corrección de entregas de alumnos, ingesta de ZIPs de Moodle / repositorios de GitHub Classroom, caché SHA-256, diff de reentregas y reporte masivo.
````

---

(manual-dredd-proposito)=
## 1. Propósito y Filosofía Pedagógica

La herramienta **`dredd`** forma parte del ecosistema oficial de software de la cátedra. Su diseño sigue principios pedagógicos rigurosos:

1. **Evidencia Técnica Directa**: Todo diagnóstico se fundamenta en la norma ISO C (C11/C23), en el modelo de memoria del sistema o en convenciones arquitectónicas formales.
2. **Acción Correctiva Concreta**: Cada advertencia incluye la prescripción técnica inmediata para resolver el defecto sin recurrir a conjeturas.
3. **Autonomía del Estudiante**: Facilita la autoevaluación local antes de la entrega final del trabajo práctico.
4. **Objetividad Docente**: Estandariza la corrección automática eliminando discrepancias subjetivas en la evaluación.

---

(manual-dredd-instalacion)=
## 2. Instalación y Diagnóstico del Entorno

````{important}
Asegurate de contar con el compilador GCC/Clang y las librerías del sistema instaladas antes de ejecutar `dredd`.
````

Para comprobar el estado de salud de tu entorno de trabajo y las dependencias auxiliares:

````{code-block} bash
# Comprobación de dependencias del sistema
dredd doctor
````

Si se detecta la falta de alguna utilidad (como `gdb`, `valgrind`, `clang-format` o `typst`), el comando indicará el paquete exacto a instalar según tu distribución GNU/Linux o entorno MSYS2.

---

(manual-dredd-comandos)=
## 3. Referencia Completa de Comandos CLI

A continuación se detallan los subcomandos principales disponibles en `dredd`:

| Sintaxis del Comando | Descripción y Efecto |
| :--- | :--- |
| `dredd eval <actividad> --all` | Evalúa en lote todas las entregas del cuatrimestre aplicando Ripley. |
| `dredd diff-submission <alumno> r1 r2` | Compara dos versiones sucesivas de la misma entrega mostrando cambios. |
| `dredd plagiarism <actividad> --threshold 0.75` | Ejecuta detección de plagio por algoritmo Winnowing y AST. |
| `dredd moodle unpack <zips_dir>` | Descomprime recursivamente las entregas bajadas del campus. |
| `dredd export-guarani <actividad> -o notas.csv` | Exporta las calificaciones en formato CSV de actas SIU Guaraní. |
| `dredd doctor` | Verifica sandboxes, compiladores y base SQLite de Dredd. |

````{tip}
Podés agregar el flag `--json` a la mayoría de los comandos para exportar resultados en formato estructurado o `--md` para generar reportes Markdown para el informe de entrega.
````

---

(manual-dredd-tutorial)=
## 4. Tutorial Paso a Paso con Ejemplos Reales

### Caso de Estudio

Considerá el siguiente fragmento de código representativo:

````{code-block} c
:linenos:
// Estructura de directorio de entregas procesada por Dredd:
// entregas/
//   ├── alumno_perez/
//   │   ├── r1/ (primera entrega)
//   │   └── r2/ (reentrega corregida)
//   └── alumno_gomez/
//       └── r1/
````

### Ejecución de la Herramienta

Ejecutá el análisis desde tu terminal:

````{code-block} bash
dredd eval <actividad> --all
````

### Salida Obtenida en Consola

````{code-block} text
[✓] 45 entregas evaluadas en 12.4s (Caché SHA-256: 38 hits / 7 evaluadas)
[✓] Reportes individuales generados: entregas/*/*_reporte.md
[✓] Análisis de Plagio: 0 coincidencias sospechosas por encima del 75%
[✓] Actas SIU Guaraní exportadas: actas_tp1.csv (42 Aprobados, 3 Desaprobados)
````

````{note}
Prestá atención a la explicación pedagógica generada: la herramienta no solo señala la línea del problema, sino que explica la causa raíz y el impacto en memoria o arquitectura.
````

---

(manual-dredd-ejercicios)=
## 5. Ejercicios Prácticos y Desafíos

Practicá el uso avanzado de **`dredd`** resolviendo los siguientes ejercicios:

````{exercise} Desafío 1: Evaluación en Lote de Entregas
Ejecutar la evaluación masiva del TP1 sobre todas las carpetas de alumnos.

**Instrucción de ejecución:**
```bash
dredd eval tp1 --all
```
````

````{solution} Desafío 1
```bash
dredd eval tp1 --all
# Verificá que la operación concluya exitosamente con código de salida 0.
```
````

````{exercise} Desafío 2: Comparativa de Reentrega (R1 vs R2)
Visualizar los cambios y funciones modificadas por un alumno en su segunda versión.

**Instrucción de ejecución:**
```bash
dredd diff-submission alumno_perez r1 r2 --md reporte_reentrega.md
```
````

````{solution} Desafío 2
```bash
dredd diff-submission alumno_perez r1 r2 --md reporte_reentrega.md
# Revisá el archivo generado o el informe en terminal para confirmar la resolución del problema.
```
````

````{exercise} Desafío 3: Detección de Plagio Cruzado
Auditar similitud estructural de código en el lote de entregas.

**Instrucción de ejecución:**
```bash
dredd plagiarism tp1 --threshold 0.70
```
````

````{solution} Desafío 3
```bash
dredd plagiarism tp1 --threshold 0.70
# Comprobá que la salida confirme la ausencia de advertencias o errores pendientes.
```
````

---

(manual-dredd-makefile)=
## 6. Integración en el Flujo de Trabajo y Makefile

Para incorporar `dredd` de forma automática a tu flujo de desarrollo, agregá la siguiente regla en el `Makefile` de tu proyecto:

````{code-block} makefile
check-dredd:
	@echo "=== Ejecutando verificación con dredd ==="
	dredd check src/ include/

.PHONY: check-dredd
````

Ejecutá `make check-dredd` antes de cada commit para asegurar que tu código conserve el estado de aprobación.
