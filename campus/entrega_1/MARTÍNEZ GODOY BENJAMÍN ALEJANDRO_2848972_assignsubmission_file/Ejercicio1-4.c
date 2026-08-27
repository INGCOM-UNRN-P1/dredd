/*
Ejercicio 1.1 -  Invertir un Número Entero
Implementar una función que tome un número entero y devuelva otro número con los dígitos en orden inverso.
-----------------
Benjamin Martinez
1-UnkNow-1
*/

#include <stdio.h>

int main ()
{
    int num = 0;
    int invertido = 0;
    int inversion = 0;
    printf("Ingrese un numero entero: ");
    scanf("%d", &num);
    while (num != 0)
    {
        inversion = num % 10;
        num = num / 10; 
        invertido = invertido * 10 + inversion;
    }
    printf("El numero invertido es: %d\n", invertido);
    return 0; 
}