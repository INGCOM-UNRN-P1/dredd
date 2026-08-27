/*
Ejercicio 1.38 – Invertir un número entero
Implementar una función que tome un número entero y devuelva otro número con los dígitos en orden inverso.
-----------------
Maia Jael Sosa
MaiaJael
*/

#include <stdio.h>

int main()
{
    int numero = 0;
    int inverso = 0;

    printf("Ingrese un número: ");
    scanf("%d", &numero);

    while(numero != 0)
    {
        int digito = numero % 10;
        inverso = (inverso * 10) + digito;
        numero = numero / 10;
    }

    printf("El número invertido es: %d", inverso);

    return 0;
}