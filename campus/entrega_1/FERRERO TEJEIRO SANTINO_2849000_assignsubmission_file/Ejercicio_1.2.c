//Ejercicio 2 - Seceuncia Ascendente
//El objetivo es mostrar una secuencia de números enteros que comienza en un número n y termina justo antes de un número m. Esto corresponde al intervalo matemático [n, m).

#include<stdio.h>
 int main(){

    int n = 0;
    int m = 0;
    int i = 0;

    printf("Ingrese el primer numero de su intervalo: \n" );
    scanf("%d", &n);
      printf("Ingrese el ultimo numero de su intervalo: \n" );
    scanf("%d", &m);

    for(int i = n ; i < m ; i++){
        printf("%d\n", i);
    }
    return 0;
 } //main

 /*
 Nombre y apellido: Ferrero Santino
 Usuario de Github: santinof256
 */