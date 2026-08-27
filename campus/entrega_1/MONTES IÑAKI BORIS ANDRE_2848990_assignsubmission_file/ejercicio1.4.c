/*
Ejercicio 1.4 – Invertir un numero entero
Implementar una función que tome un número entero y devuelva otro número con los dígitos en orden inverso.
-----------------
Iñaki Montes
iniaki12
*/

#include<stdio.h>
int main()
{
    int numero;
    int digitos;
    printf("ingresar numero: \n");
    scanf("%d", &numero);
    if (numero < 0)
    {
        printf("debe ser positivo");
        return 1;
    }
    while(numero > 0)
    {
        digitos = numero % 10;
        printf("%d", digitos);
        numero /= 10;
    }
    printf("\n");
    return 0;
}