/*
Ejercicio 1.2 – Secuencia Ascendente
El objetivo es mostrar una secuencia de números enteros,
que comienza en un número n y termina justo antes de un número m. 
Esto corresponde al intervalo matemático [n, m).
-----------------
Nombre y Apellido: Fasuto Tomas Sala
Usuario Github: tomassala1
*/

// main
#include <stdio.h>

int main(){
    int n,m,i;

    printf("Ingrese el valor con el que desea iniciar: ");
    scanf("%d", &n);

    printf("Ingrese el valor limite: ");
    scanf("%d", &m);

    for (i = n; i < m; i++) {
        printf("%d\n", i);
    }

    return 0;
}