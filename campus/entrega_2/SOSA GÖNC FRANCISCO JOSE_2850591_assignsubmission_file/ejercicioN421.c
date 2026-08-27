/*
ejercicio 4.21 - validacion de entrada
Leé un número entre 1 y 100. Si está fuera de rango, pedí nuevamente hasta que sea válido.
-------------------
Francisco Sosa Gonc
sancocho192
*/
#include <stdio.h>

int main() {
    int inicial = 1;
    int final = 100;
    int num;
    do
    { printf("ingrese un numero entro del rango (1-100)\n");
    scanf( "%d", &num); } 
    while (num <1 || num >100);

    printf("se ingreso un numero dentro del rango\n");
    return 0;

}