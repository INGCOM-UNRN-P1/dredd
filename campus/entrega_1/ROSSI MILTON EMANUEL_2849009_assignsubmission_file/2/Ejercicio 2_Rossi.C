/*
Ejercicio 2 – Secuencia Ascendente
El objetivo es mostrar una secuencia de números enteros que comienza en un número n y 
termina justo antes de un número m. Esto corresponde al intervalo matemático [n, m).

-----------------
Nombre y Apellido: Milton Rossi
Usuario Github: milton1000
*/
#include<stdio.h>

int main() {

    int numero_m = 0;
    int numero_n = 0;

    printf("Ingrese un numero n:");
    scanf("%d",&numero_n);
    printf("ingrese un segundo numero m:");
    scanf("%d",&numero_m);

    for(int i = numero_n ; i < numero_m ; i++) {
        
        printf("%d\n",i);
    }   
    
    return 0;
}