# Changelog

Todos los cambios notables de este proyecto se documentan en este archivo.
Formato basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/);
versiones según [SemVer](https://semver.org/lang/es/).

## [Sin publicar]

### Agregado

- **targets del docente**: `targets_docente` en la regla de la actividad (la carpeta de `deckard guide practica`): la evaluación copia `dredd.mk` y `.dredd/` en la entrega, corre cada `make dredd-…` en los ejercicios declarados, los suma al informe (sólo los visibles para el alumno) y a la nota de pruebas según su peso, y descarta e informa un `dredd.mk` o un target `dredd-…` propio de la entrega; `config validate` los verifica (Ola 30).
- **makefiles individuales**: dentro de `ejercicios/` vale cualquier nombre de carpeta (los ids del banco de las prácticas generadas), no sólo `ejercicioN` (Ola 30).
- **cohorte**: `dredd cohorte <carpeta>` arma la planilla de seguimiento de una cohorte de GitHub Classroom (un repo clonado por alumno): estado de cada entrega con el veredicto de perfil de ripley, observaciones más frecuentes con enlace al apunte y tiempos (commits del alumno, último commit y atraso respecto de `--fecha-limite`), en `cohorte.csv`, `cohorte.md` y `cohorte.json`. Lo usa sulaco `cohorte.yml` (Ola 25).
- **cohorte**: índice de error por concepto (porcentaje de entregas analizadas con observaciones del tema) en `cohorte.md` y en `conceptos.md`, un informe anónimo (sin nombres ni repos) para compartir con todo el equipo; con el cron semanal de sulaco `cohorte.yml` es el informe semanal de qué reforzar en clase. `cluster-errors` y `cohorte` comparten el cálculo (`cohorte.agrupar`) (Ola 26).

## [2.1.0] - 2026-09-28

Primera versión con registro de cambios; lo anterior está en el historial de git.

### Agregado

- **cli**: cumplir el contrato de línea de comandos de LINEAMIENTOS §3.2 (N-ECO-04) (`da50a96`)

### Corregido

- **cli**: mostrar los errores de uso como mensajes en lugar de tracebacks (N-ECO-05, N-DREDD-05) (`6fe758d`)
- **tipos**: importar los nombres de typing usados en anotaciones (N-ECO-08) (`45676d0`)
- **export**: evitar el bucle infinito de export-report con líneas que empiezan con # o | (N-DREDD-01) (`6f3ff03`)
- **sandbox**: no montar la raíz del disco al ejecutar entregas (N-DREDD-02) (`4aac96f`)

### Documentación

- incorporar manual de uso integral y referencia tecnica (dredd) (`b30e651`)

### Mantenimiento

- **calidad**: verificar errores de Python y dependencias vulnerables (N-ECO-08, N-ECO-13) (`65b5f11`)
- **deps**: mover las dependencias de desarrollo a dependency-groups (N-ECO-07) (`3741cdc`)
