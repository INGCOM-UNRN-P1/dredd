/*
ejercicio 4.19 - numeros pares en rango
Mostrá todos los números pares entre dos valores ingresados.
-------------------
Francisco Sosa Gonc
sancocho192
*/
#include <stdio.h>
 int main(){
    int inicio;
    int final;
    int i = 0;
    printf("ingrese numero inicial:\n");
    scanf( "%d", &inicio);
    printf("ingrese numero final:\n");
    scanf("%d", &final);

    printf("los numeros pares entre esos numeros son:\n");
    for (i = inicio; i <= final; i++) {
        if (i % 2 == 0){
            printf("%d\n", i);
        }
    }
    return 0;
 }