/*
Ejercicio 1.38 - Invertir un Número Entero
"En este ejercicio se va a iterar sobre un numero tomado del usuario para invertir el orden de sus digitos
Esto nos va a ayudar a aprender iterado sobre cadenas"
-----------------
Nombre y Apellido: Mateo Cucurull
Usuario de GitHub: MattCucurull
*/
#include <stdio.h>

int main() {
    /* Para la definición de variables se tienen en cuenta 3 integrales:*/
    int numero = 0; /**/
    int digito = 0; /**/
    int invertido = 0; /* Una donde se va a mostrar el codigo inverso final */

    printf("Ingrese un numero para invertir sus digitos que no sea 0:\n");
    scanf("%d", &numero);

    if (numero != 0){
        while (numero != 0){
            digito = numero % 10;
            invertido = (invertido * 10) + digito;
            numero = numero / 10;
        }
        printf("Tu numero invertido es %d", invertido);
    }
    else {
        printf("Tu numero no va a poder ser procesado porque es igual a 0");
    }
    return 0;
}