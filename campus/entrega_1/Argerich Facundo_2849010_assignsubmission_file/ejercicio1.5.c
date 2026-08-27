/*
Ejercicio 5 – Contador de digitos 
Crear una función que reciba un número entero y devuelva la cantidad de dígitos que lo componen.
-----------------
Facundo Argerich
Github: ArgerichFacu
*/

#include <stdio.h>

int main ()
{
    int num = 0;
    int dig = 0;

    printf("Ingrese un numero: \n");
    scanf("%d", &num);

    while (num > 0)
    {
        num = num / 10;
        dig = dig + 1;
    }
    
    printf("El numero tiene %d digitos", dig);
    return 0;
}