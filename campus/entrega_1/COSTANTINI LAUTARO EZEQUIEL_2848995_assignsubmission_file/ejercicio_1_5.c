/*
Ejercicio 1.5 - Contador de Dígitos ⭐⭐⭐☆☆
Crear una función que reciba un número entero y devuelva la
cantidad de dígitos que lo componen.
-----------------
Nombre y Apellido: Lautaro Costantini
Usuario Github: L-Ezql
*/

#include <stdio.h>

int main()
{
    int numero = 0;
    int cantidad_digitos = 0;
    printf("Ingresar numero: ");
    scanf("%d", &numero);
    int numero2 = numero;

    if(numero == 0)
    {
        cantidad_digitos = cantidad_digitos + 1;
    }
    else 
    {
        while(numero != 0)
        {
            cantidad_digitos = cantidad_digitos + 1;
            numero = numero / 10;
        }
    }
    printf(" El numero %d tiene %d digitos", numero2, cantidad_digitos);
    return 0;
}