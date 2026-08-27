/*
Ejercicio 1.5 - Contador de Digitos
Crear una función que reciba un número entero y devuelva la cantidad de dígitos que lo componen.

------------------

Anthony Alexis Nicloux
alex44523
*/

#include <stdio.h>
// Biblioteca que tiene el Valor Absoluto
#include <stdlib.h>

int main(){
    int numero = 0;
    int i = 0;
    scanf ("%d", &numero);
    // Para que siempre los numeros sean positivos
    int numero_abs = abs(numero);
    if (numero == 0){
        printf ("Tiene 1 digito\n");
        return 0;
    }
    while (numero_abs > 0){
        numero_abs = numero_abs / 10;
        i++;
    }
    printf ("Tiene %d digitos", i);
    return 0;
}