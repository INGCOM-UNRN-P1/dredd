/*
Ejercicio 3: Determinar si un número es par o impar
Este es un ejercicio fundamental de lógica condicional. 
El programa debe solicitar un número entero al usuario y determinar si es par (divisible por 2) o impar.
Nombre y apellido: Yucra Agustin
Usuario de Github: 08agus00
*/
//main



#include <stdio.h>
int main() {
    int numero = 0;
    printf("Ingrese un numero: ");
    scanf("%d", &numero);
    if (numero % 2 == 0) {
        printf("El numero %d es par\n", numero);
    } else {
        printf("El numero %d es impar\n", numero);
    }
    return 0;
    }