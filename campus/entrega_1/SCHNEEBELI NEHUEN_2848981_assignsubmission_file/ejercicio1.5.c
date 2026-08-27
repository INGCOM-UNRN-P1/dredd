/*
 * Ejercicio 1.5 - Contador de digitos.
 * Crear una función que reciba un número entero y devuelva la cantidad de dígitos que lo componen.
 * 
 * Nombre y Apellido: Nehuen Schneebeli.
 * github: NehuenSch.
 */

#include <stdio.h>

int main()
{
    int numero = 0;
    int i = 0;
    
    printf("Ingrse un numero: ");
    scanf("%d", &numero);

    while(numero > 0)
    {
        numero = numero / 10;
	i = i + 1;
    }

    printf("El numero ingresado tiene: %d\n", i);
    return 0;
}

