/*
Ejercicio 2 – Secuencia Ascendente
El objetivo es mostrar una secuencia de números enteros que comienza en un número n y 
termina justo antes de un número m. Esto corresponde al intervalo matemático [n, m).

-----------------
Nombre y Apellido: Milton Rossi
Usuario Github: milton1000
*/
#include<stdio.h>

int main(){

    int numero_1 =0;
    int numero_2 =0;

        printf("Ingrese un numero:");
        scanf("%d",&numero_1);
        printf("ingrese un segundo numero:");
        scanf("%d",&numero_2);

            for(int i= numero_1;i<numero_2;i++){
                
                printf("%d\n",i);
            }   
return 0;
}