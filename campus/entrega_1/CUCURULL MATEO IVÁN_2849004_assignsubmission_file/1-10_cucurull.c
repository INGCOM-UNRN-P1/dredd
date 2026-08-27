/*
Ejercicio 1.10 - Par o Impar
"En este ejercicio se toma un único número entero con el que se va a verificar si es par o no usando la operación modulo (%)
Esto va a servir para aprender el uso de estructuras condicionales simples"
------------------
Nombre y Apellido: Mateo Cucurull
Usuario de Github: MattCucurull
*/
#include <stdio.h>

int main() {
    int numero = 0;

    printf("Ingrese un numero entero para evaluar si es par o impar");
    scanf("%d", &numero);
    
    if (numero % 2 == 0){
        printf("Tu numero %d es par", numero);
    }
    else{
        printf("Tu numero %d es impar", numero);
    }
    return 0;
}