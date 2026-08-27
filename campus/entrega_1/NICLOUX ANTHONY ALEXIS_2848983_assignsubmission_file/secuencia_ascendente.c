/* 
Ejercicio 1.2 - Secuencia Ascendente
El objetivo es mostrar una secuencia de números enteros
que comienza en un número n y termina justo antes de un
número m. Esto corresponde al intervalo matemático [n, m).

-----------------

Anthony Alexis Nicloux
alex44523
*/

#include <stdio.h>

int main(){
    int n = 0;
    int m = 0;
    int i = 0;
    scanf ("%d", &n);
    scanf ("%d", &m);
    for (i = n; i < m; i++){
        printf ("% d", i);
    }
    return 0;
}