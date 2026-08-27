/*
Ejercicio 1.3 - Par o impar
Este es un ejercicio fundamental de lógica condicional. El programa debe solicitar un número entero
al usuario y determinar si es par (divisible por 2) o impar.
-----------------
Maximiliano Vargas
vsmaxy
*/
#include <stdio.h>

int main(){
    int num = 0;
    printf("Ingrese un numero: ");
    scanf("%d", &num);
    if(num % 2 == 0){
        printf("%d es par",num);
    }else{
        printf("%d es impar",num);
    }
    return 0;
}