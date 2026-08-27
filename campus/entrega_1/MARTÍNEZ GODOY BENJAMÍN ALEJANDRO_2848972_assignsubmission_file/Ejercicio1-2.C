/*
Ejercicio 1.2 - Secuencia Ascendente.
El objetivo es mostrar una secuencia de números enteros que comienza en un número n y termina justo antes de un número m.
-----------------
Benjamin Martinez
1-UnkNow-1
*/
#include <stdio.h>

int main()
{
    int n = 0;
    int m = 0;
    int i = 0;
    printf("Ingrese un numero entero: ");
    scanf("%d", &n);
    printf("Ingrese otro numero entero: ");
    scanf("%d", &m);
   for(i=n; i<m; i++)
   {
       printf("%d \n", i);
   }
   return 0;
}