# Changelog

Todos los cambios notables de este proyecto se documentan en este archivo.
Formato basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/);
versiones según [SemVer](https://semver.org/lang/es/).

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
