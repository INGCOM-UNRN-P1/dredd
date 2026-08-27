/*
Ejercicio 3 – Par o Impar
Este programa debe solicitar un número entero al usuario y determinar
si es par(divisible por 2) o impar
-----------------
Dulce Piciana
dulcepiciana
*/
#include<stdio.h>
int main()
{
    int numero=0;
    printf("Ingrese número entero:");
    scanf("%d",&numero);
    if(numero % 2==0)
    {
        printf("Numero es par!");
    }
    else{
        printf("Numero no es par!");
    }
    return 0;
}