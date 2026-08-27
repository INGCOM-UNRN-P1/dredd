/*
Ejercicio 3 - Par o Impar
------------------
Francisco Sosa Gonc
sancocho192
*/
#include <stdio.h>

int main() {
    int numero;

    printf("ingrese un numero:");
    scanf("%d", &numero);

    if (numero % 2 == 0){
        printf("el numero es par");
    } else {
        printf("el numero es impar");
    }

    return 0;
}
