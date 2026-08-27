/*
Ejercicio 1.4 - Invertir un Numero Entero

Implementar una función que tome un número entero y devuelva otro número con los dígitos en orden inverso.

Danco Ormaechea
github: DancoOrmaechea
*/
#include <stdio.h>
int invertirDigitos(int num)
{
    int invertido = 0;
    while (num != 0)
    {
        int digito = num % 10;               // Obtiene el último dígito
        invertido = invertido * 10 + digito; // Añade el dígito a la izquierda
        num /= 10;                           // Elimina el último dígito
    }
    return invertido;
}
int main()
{
    int num = 0;

    printf("Ingrese un numero entero: ");
    scanf("%d", &num);

    int invertido = invertirDigitos(num);
    printf("El numero invertido es: %d\n", invertido);

    return 0;
}