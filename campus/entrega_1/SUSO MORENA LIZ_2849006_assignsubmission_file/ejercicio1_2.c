/*
Ejercicio 2 - Secuencia Ascendente
El objetivo es mostrar una secuencia de 
números enteros que comienza en un número n 
y termina justo antes de un número m. Esto corresponde al 
intervalo matemático [n, m).
-----------------
Morena Suso
MorenaSuso
*/

// main

#include <stdio.h>

int main()
{
    int n = 0;
    int m = 0;
    int aux = 0;
    printf("Desde que numero (incluido): \n");
    scanf("%d" , &n);
    printf("Hasta que numero (no incluido): \n");
    scanf("%d" , &m);

    for(aux = n; aux < m; aux++)
    {
        printf("%d\n" , aux);
    }
    return 0;
}