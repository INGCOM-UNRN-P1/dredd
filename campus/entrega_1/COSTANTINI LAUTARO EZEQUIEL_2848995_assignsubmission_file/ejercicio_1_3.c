/*
Ejercicio 1.3 - Par o Impar ⭐⭐☆☆☆
Este es un ejercicio fundamental de lógica condicional.
El programa debe solicitar un número entero al usuario y
determinar si es par (divisible por 2) o impar.
-----------------
Nombre y Apellido: Lautaro Costantini
Usuario Github: L-Ezql
*/

#include <stdio.h>

int main()
{
    int n = 0;
    printf("Ingrese un numero: ");
    scanf("%d", &n);
    if(n % 2 == 0){
        printf("%d es par\n", n);
    } else {
        printf("%d es impar\n", n);
    }
    return 0;
}