/*
Ejercicio 1.2 - Secuencia Ascendente ⭐☆☆☆☆
El objetivo es mostrar una secuencia de números enteros
que comienza en un número n y termina justo antes de un número m.
Esto corresponde al intervalo matemático [n, m).
-----------------
Nombre y Apellido: Lautaro Costantini
Usuario Github: L-Ezql
*/

#include <stdio.h>

int main()
{
    int n = 0;
    int m = 0;
    printf("Numero donde iniciar la secuencia: ");
    scanf("%d", &n);
    printf("Numero donde finalizar la secuencia: ");
    scanf("%d", &m);
    for(int i = n; i < m; i++){
        printf("%d\n", i);
    }
    return 0;
}