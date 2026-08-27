//Ejercicio 4 - Invertir un Numero Entero
//Implementar una función que tome un número entero y devuelva otro número con los dígitos en orden inverso.

#include<stdio.h>
int main(){

    int invertido = 0;
    int num = 0;
    int digito = 0;

    printf("Ingrese un numero:\n");
    scanf("%d", &num);

    while(num != 0)
    {
        digito = num % 10;

        invertido = (invertido * 10) + digito;

        num = num / 10;

    }

    printf("%d\n", invertido);

    return 0;
} //main

/*
Nombre y apellido: Ferrero Santino
Usuario de Github: santinof256
 */