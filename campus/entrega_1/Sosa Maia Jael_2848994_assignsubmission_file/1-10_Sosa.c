/*
Ejercicio 1.10 – Par o impar
Este es un ejercicio fundamental de lógica condicional. 
El programa debe solicitar un número entero al usuario y determinar si es par (divisible por 2) o impar.
-----------------
Maia Jael Sosa
MaiaJael
*/

#include <stdio.h>

int main()
{
    int numero = 0;

    printf("Ingresar un número: ");
    scanf("%d", &numero);

    if(numero % 2 == 0)
    {
        printf("El número %d es par.", numero);
    }
    else
    {
        printf("El número %d es impar", numero);
    }

    return 0;
}