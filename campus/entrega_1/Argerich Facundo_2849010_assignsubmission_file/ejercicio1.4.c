/*
Ejercicio 4 – Invertir un Número 
Implementar una función que tome un número entero y devuelva otro número con los dígitos en orden inverso.
-----------------
Facundo Argerich
Github: ArgerichFacu
*/

#include <stdio.h>
#include <stdlib.h>

int main ()
{
    int num = 0;
    int num_invertido = 0;

    printf("Ingrese un numero entero: \n");
    scanf("%d", &num);

    if (num > 0)
    {
        while (num > 0)
        {
            num_invertido = num % 10;
            num = num / 10;
            printf("%d", num_invertido);
        }
    }
    else
    {
        num = abs(num);
        printf("-");
        while (num > 0)
        {
            num_invertido = num % 10;
            num = num / 10;
            printf("%d", num_invertido);
        }
    }

    return 0;
}