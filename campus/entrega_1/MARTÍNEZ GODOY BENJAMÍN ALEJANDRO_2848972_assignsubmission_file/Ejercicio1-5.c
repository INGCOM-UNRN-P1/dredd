/*
Ejercicio 1.1 - Contador de digitos
Crear una función que reciba un número entero y devuelva la cantidad de dígitos que lo componen.
-----------------
Benjamin Martinez
1-UnkNow-1
*/
#include <stdio.h>

int main ()
{
    int num = 0;
    int contador = 0;
    printf("Ingrese un numero entero: ");
    scanf("%d", &num);
    if (num == 0) 
    {
        contador = 1; // El número 0 tiene 1 dígito
    }
    while (num != 0)
    {
        num = num / 10;
        contador++;
    }
    printf("El numero tiene %d digito/s\n", contador);
    return 0;
}