/*
Ejercicio 4 – Invertir un Número Entero
Implementar una función que tome un número entero y devuelva otro número con los dígitos en orden inverso.

-----------------
Nombre y Apellido: Milton Rossi
Usuario Github: milton1000
*/
#include <stdio.h>

int main () {

    int numero_entero = 0;
    int invertido = 0;
    int digito = 0;

        printf("Ingrese un numero entero:");
        scanf("%d",&numero_entero);
            
        while(numero_entero > 0) {

            digito = numero_entero % 10;
            invertido = (invertido * 10) + digito;
            numero_entero = numero_entero / 10;
            }
                
    printf("El numero invertido es: %d",invertido);

    return 0;
}
