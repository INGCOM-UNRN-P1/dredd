/*
Ejercicio 2 - Secuencia Ascendente
------------------
Francisco Sosa Gonc
sancocho192
*/
#include <stdio.h>

int main() {
    int inicio;
    int fin;

    printf("ingrese el primer numero:");
    scanf("%d", &inicio);

    printf("ingrese el ultimo numero:");
    scanf("%d", &fin);

    printf("secuencia de numeros entre el primero y el ultimo:\n");
    for (int i = inicio; i < fin; i++) {
        printf("%d", i);
    }

    printf("\n");
    return 0;
}