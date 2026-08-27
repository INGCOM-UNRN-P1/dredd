/*
Ejercicio 1.4 - Invertir un Número Entero ⭐⭐☆☆☆
Implementar una función que tome un número entero y devuelva
otro número con los dígitos en orden inverso.
-----------------
Nombre y Apellido: Lautaro Costantini
Usuario Github: L-Ezql
*/

#include <stdio.h>

int main()
{
    int numero = 0;
    int numero_invertido = 0;
    printf("Ingrese un numero: ");
    scanf("%d", &numero);
    while (numero != 0){
        int ultimo_digito = numero % 10;
        numero_invertido = numero_invertido * 10 + ultimo_digito;
        numero = numero / 10;
    }
    printf("El numero invertido es: %d\n", numero_invertido);
    return 0;
}