/*
Ejercicio 2.1 – Secuencia Ascendente
El objetivo es mostrar una secuencia de números enteros que comienza en un número n y termina 
justo antes de un número m. Esto corresponde al intervalo matemático [n, m).
-----------------
Franco Martinez
Usuario Github : Fr4ncos7
*/

#include <stdio.h>

int main()
{
    int inclusive = 0;
    int exclusive = 0;

    printf("ingiese un numero: \n");
    scanf("%d", &inclusive);
    printf("ingrese otro numero pero menor al anterior numero ingresado: \n");
    scanf("%d", &exclusive);
    printf("---------------------------- \n");

    for ( int i = inclusive; i > exclusive; i--)
    {
        printf("%d \n", i);
    }
    return 0;
}