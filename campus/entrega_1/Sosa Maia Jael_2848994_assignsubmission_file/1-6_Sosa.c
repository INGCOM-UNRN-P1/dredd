/*
Ejercicio 1.6 – Secuencia Ascendente
El objetivo es mostrar una secuencia de números enteros que comienza en un número n y termina
justo antes de un número m. Esto corresponde al intervalo matemático [n, m).
-----------------
Maia Jael Sosa
MaiaJael
*/

#include <stdio.h>

int main()
{
    int n = 0;
    int m = 0;

    printf("Ingrese el número \"n\":");
    scanf("%d", &n);

    do
    {
        printf("Ingrese el número \"m\":");
        scanf("%d", &m);

        if(m <= n)
        {
            printf("ERROR: El número debe ser mayor a n (%d). \n", n);
        }
    } while(m <= n);

    for(int i = n; i < m; i++)
    {
        if(i != (m -1))
        {
            printf("%d, ", i);
        }
        else
        {
            printf("%d \n", i);
        }
    }

    return 0;
}