/*
Ejercicio 1.3 – Par o Impar
El programa debe solicitar un número entero al usuario y determinar si es par (divisible por 2) o impar.
-----------------
Iñaki Montes
iniaki12
*/

#include <stdio.h>
int main()
{
    int numero = 0; 
    printf("por favor ingrese un valor: ");
    scanf("%d", &numero);
    if (numero % 2 == 0)
    {
        printf("el numero %d es par\n", numero);
    }
    else
    {
        printf("el numero %d es impar\n", numero);
    }
    return 0;
}