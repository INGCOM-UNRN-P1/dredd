/*
Ejercicio 1.2 – Secuencia ascendente
El objetivo es mostrar una secuencia de números enteros que comienza en un número n y termina justo antes de un número m.
Esto corresponde al intervalo matemático [n, m).
-----------------
Iñaki Montes
iniaki12
*/

#include <stdio.h>
int main()
{
    int n = 0;
    int m = 0;
    int i = 0;
    printf("ingresar valor n: ");
    scanf("%d", &n);
    printf("ingresar valor m: ");
    scanf("%d", &m);
    for(i = n; i < m; i++)
    {
        printf("%d\n", i);
    }
    return 0;
}