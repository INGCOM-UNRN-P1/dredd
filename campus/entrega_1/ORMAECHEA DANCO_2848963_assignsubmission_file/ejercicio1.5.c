/*
Ejercicio 1.5 - Contador de Digitos

Crear una función que reciba un número entero y devuelva la cantidad de dígitos que lo componen.

Danco Ormaechea
github: DancoOrmaechea
*/
#include <stdio.h>

int contarDigitos(int num)
{
    int digitos = 0;

    if (num == 0)
    {
        return 1;
    }

    while (num != 0)
    {
        num /= 10; // Elimina el último dígito
        digitos++;
    }
    return digitos;
}
int main()
{
    int num = 0;
    printf("ingrese numero entero natural : ");
    scanf("%d", &num);

    int digitos = contarDigitos(num);
    printf("La cantidad de digitos del numero es: %d\n", digitos);
    return 0;
}