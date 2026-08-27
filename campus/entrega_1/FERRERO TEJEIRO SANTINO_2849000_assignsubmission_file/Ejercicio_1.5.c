//Ejercicio 5 - Contador de digitos
//Crear una función que reciba un número entero y devuelva la cantidad de dígitos que lo componen.

#include <stdio.h>
#include <stdlib.h>
int main(){

    int num = 0;
    int contador = 0;
    int numero_abs;

    printf("Ingrese un numero: \n");
    scanf("%d", &num);

    if (num == 0){
        printf ("1\n");
    }
    else {
    numero_abs = abs(num);

   while (numero_abs > 0){
    numero_abs = numero_abs / 10;
    contador = contador + 1;
   }
    printf("%d\n", contador);
   }
    return 0;
} //main

/*
Nombre y apellido: Ferrero Santino
Usuario de Github: santinof256
*/