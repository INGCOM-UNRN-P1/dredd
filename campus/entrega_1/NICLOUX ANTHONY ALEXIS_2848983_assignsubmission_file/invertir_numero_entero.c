/*
Ejercicio 1.4 - Invertir un número entero
Implementar una función que tome un número entero y devuelva otro número con los dígitos en orden inverso.

-----------------------

Anthony Nicloux
alex44523
*/

#include <stdio.h>

int main(){
    int numero = 0;
    int invertido = 0;
    int digito = 0;
    scanf ("%d", &numero);
    // Si el ultimo digito es 0 no lo muestra
    while (numero != 0){
        digito = numero % 10;
        invertido = (invertido * 10) + digito;
        numero = numero / 10;
    }
    printf ("El numero invertido es %d\n", invertido);
    return 0;
}