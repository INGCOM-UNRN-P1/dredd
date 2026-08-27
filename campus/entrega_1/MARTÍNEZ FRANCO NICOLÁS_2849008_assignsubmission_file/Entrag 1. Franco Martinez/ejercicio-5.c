/*
Ejercicio 5.1 – Contador de Dígitos
Crear una función que reciba un número entero y devuelva la cantidad de
dígitos que lo componen.
-----------------
Franco Martinez
Usuario Github : Fr4ncos7
*/

#include <stdio.h>

int main()
{
    int numero = 0;
    int cant_digitos= 0;

    printf("Ingrese un numero: \n");
    scanf("%d", &numero);

    if (numero > 0)
    {
        while (numero > 0)
        {
            numero = numero / 10; 
            cant_digitos = cant_digitos + 1;
        }
    
        printf("Este numero tiene %d digitos. \n", cant_digitos);
    }
    else if (numero < 0)
    {
        numero = numero * (-1);

        while (numero > 0)
        {
            numero = numero / 10; 
            cant_digitos = cant_digitos + 1;
        }
    
        printf("Este numero tiene %d digitos. \n", cant_digitos);
    }
    else
    {
        cant_digitos = 1;
        printf("Este numero tiene %d digito. \n", cant_digitos);
    }
    
    return 0;
}