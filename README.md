# dredd
El Juez de los Practicos

Este script llama al compilador, cppcheck y splint para ver como estan
los archivos `.c` en la raíz del repositorio.

## Prerequisitos

 * `gcc`, https://gcc.gnu.org/
 * `cppcheck` - https://cppcheck.sourceforge.io/
 * `splint` - https://splint.org/
 
 Estas herramientas estan a un `apt get` de distancia, no esta pensado su uso
 en Windows, pero no hay razón para que funcione de la misma manera en un 
 entorno similar como mingw.
