/*
Ejercicio 2 – Secuencia Ascendente
El objetivo es mostrar una secuencia de números enteros que comienza en un número n y termina justo antes de un número m. Esto corresponde al intervalo matemático [n, m).
-----------------
Facundo Argerich
Github: ArgerichFacu
*/

#include <stdio.h>

int main ()
{
    int n = 0;
    int m = 0;

    printf("Ingrese el valor inicial: \n");
    scanf("%d", &n);

    printf("Ingrese el limite: \n");
    scanf("%d", &m);

    if (m < n)
    {
        printf("Ingrese un número mayor al valor inicial.");
        return 1;
    }
    
    for (int i = 0; n < m; i++) 
    {
        printf("%d ", n);
        n++;
    }
    return 0;
}