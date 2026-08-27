/*
Ejercicio 1.3 - Par o Impar
Escribir un programa que solicite un número entero al usuario y determine si es par (divisible por 2) o impar.
-----------------
Benjamin Martinez
1-UnkNow-1
*/
#include <stdio.h>

int main()
{
    int num = 0;
    printf("Ingrese un numero entero: ");
    scanf("%d", &num);
    if (num % 2 == 0)
    {
        printf("El numero %d es par.\n", num);
    }
    else
    {
        printf("El numero %d es impar.\n", num);
    }
    return 0;
}