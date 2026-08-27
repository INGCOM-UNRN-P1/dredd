/*
Ejercicio 4.1 – Invertir un Número Entero
Implementar una función que tome un número entero y devuelva
 otro número con los dígitos en orden inverso.
-----------------
Franco Martinez
Usuario Github : Fr4ncos7
*/

#include <stdio.h>

int main()
{
    int numero = 0;
    int digito = 0;
    int invertido = 0;

    printf("Ingrese un numero mayor o igual a 10 \n");
    scanf("%d", &numero);

    if (numero < 10)
    {
        printf("Debe ingresar un numero mayor o igual a 10 \n");
    }
    else
    {
        while (numero > 0)
        {
            digito = numero % 10;
            invertido = (invertido * 10) + digito;
            numero = numero / 10; 
        }
        
        printf("El numero invertido es:  %d \n", invertido);
    }
    return 0;
}