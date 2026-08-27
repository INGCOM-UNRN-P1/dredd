/*
ejercicio 4.16 - suma de N numeros
Leé un número N y calculá la suma de los primeros N números naturales.
-------------------
Francisco Sosa Gonc
sancocho192
*/

#include <stdio.h>
int main() {
    int N ;
    int suma = 0;
    printf("ingrese un numero natural\n");
    scanf( "%d", &N);

    for (int i = 1; i <= N; i++)
    {
        suma += i;
    }
    printf ("la suma de los numeros hasta el numero %d es: %d\n",N, suma);
    return 0;
}