/*
Ejercicio 1.4 – Invertir un Numero Entero
Implementar una función que tome un número entero 
y devuelva otro número con los dígitos en orden inverso.
-----------------
Nombre y Apellido: Fasuto Tomas Sala
Usuario Github: tomassala1
*/

// main
#include <stdio.h>

int main(){
    int n, digitos, invertido = 0;

    printf("Ingrese el numero a invertir: ");
    scanf("%d", &n);

    while (n > 0) {
        digitos = n % 10;
        invertido = (invertido * 10) + digitos;
        n = n / 10;
    }

    printf("El numero invertido es %d\n", invertido);

    return 0;
}