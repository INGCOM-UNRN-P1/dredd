/*
Ejercicio 1.3 - Par o Impar

Este es un ejercicio fundamental de lógica condicional.
El programa debe solicitar un número entero al usuario y determinar si es par (divisible por 2) o impar.

Danco Ormaechea
github: DancoOrmaechea
*/

#include <stdio.h>
int main()
{
    int m = 0;

    printf("ingrese un numero entero: \n");
    scanf("%d", &m);

    if (m % 2 == 0)
    {
        printf("%d es un numero par", m);
    }
    else
    {
        printf("%d es un numero impar", m);
    }
    return 0;
}