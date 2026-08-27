/*
Ejercicio 1.2 - Secuencia Ascendente

El objetivo es mostrar una secuencia de números enteros que comienza en un número n y termina justo antes de un número m.
Esto corresponde al intervalo matemático [n, m).

Danco Ormaechea
github: DancoOrmaechea
*/
#include <stdio.h>
int main()
{
    int n = 0;
    int m = 0;
    printf("ingrese un numero entero n : ");
    scanf("%d", &n);
    printf("ingrese un numero entero m :");
    scanf("%d", &m);

    if (n >= m)
    {
        printf("El valor de n debe ser menor que el valor de m.\n");
        return 1; // Salir del programa con un error
    }

    for (int i = n; i < m; i++)
    {
        printf("%d", i);
        printf("    ");
    }

    printf("\n");
    return 0;
}