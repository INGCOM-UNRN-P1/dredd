/*
Ejercicio 2 – Secuencia Ascendente
Mostrar una secuencia de números enteros que comienza en un número n 
y termina justo antes de un número m.
-----------------
Dulce Piciana
dulcepiciana
*/
#include<stdio.h>

int main(void)
{
    int m=0;
    printf("Ingrese valor límite:");
    scanf("%d", &m);
    for( int n=0; n<m;n++)
    {
        printf("n vale %d\n",n);
    }
    return 0;
}