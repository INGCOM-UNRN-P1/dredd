/*
Ejercicio 1.2 - Secuencia ascendente
El objetivo es mostrar una secuencia de números enteros que comienza en un número n y termina justo
antes de un número m. Esto corresponde al intervalo matemático [n, m).
-----------------
Maximiliano Vargas
vsmaxy
*/
#include <stdio.h>

int main(){
    int n=0;
    int m=0;
    printf("Ingrese n: ");
    scanf("%d", &n);
    printf("Ingrese m: ");
    scanf("%d", &m);
    for(int i=n; i<m; i++){
        printf("%d\n",i);
    }
    return 0;
}