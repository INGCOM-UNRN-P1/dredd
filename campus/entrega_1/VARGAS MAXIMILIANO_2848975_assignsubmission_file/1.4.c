/*
Ejercicio 1.4 - Invertir un numero entero
Implementar una función que tome un número entero y devuelva otro número con los dígitos en orden inverso.
-----------------
Maximiliano Vargas
vsmaxy
*/
#include <stdio.h>
int invertido(int num)
{
    int resultado = 0;
    int resto = 0;

    while(num != 0)
    {
        resto = num % 10;
        resultado = resultado*10 + resto;
        num = num /10;
    }
    return resultado; 
}
int main(){
    int numero = 0;
    int resultado = 0;
    printf("Ingrese un numero: ");
    scanf("%d",&numero);
    resultado = invertido(numero);
    printf("%d invertido es %d",numero,resultado);
    
    return 0;
}