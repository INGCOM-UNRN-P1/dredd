/*
Ejercicio 2 - Secuencia ascendente
El objetivo es mostrar una secuencia de números enteros que comienza en un número n y termina justo antes de un número m.
 Esto corresponde al intervalo matemático [n, m).
Nombre y apellido: Yucra Agustin
Usuario de Github: 08agus00
 */
//main

#include <stdio.h>
int main() {
    int numero1, numero2, contador = 0;
    printf("Ingrese el primer numero: ");
    scanf("%d", &numero1);
    printf("Ingrese el segundo numero: ");
    scanf("%d", &numero2);
    contador = numero1;
    while (contador < numero2) {
        printf("%d\n", contador);
        contador++;
    }
    return 0;
}
