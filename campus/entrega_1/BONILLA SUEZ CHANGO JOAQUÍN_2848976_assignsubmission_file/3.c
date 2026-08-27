/*
Ejercicio 3 - Par o Impar
Este es un ejercicio fundamental de lógica condicional. El programa debe solicitar
 un número entero al usuario y determinar si es par (divisible por 2) o impar.

Chango Joaquin Bonilla Suez
https://github.com/ysin-war
*/

#include <stdio.h>

int main(){
    int n = 0;
    printf("Ingrese un numero\n");
    scanf("%d", &n);
    if (n % 2 == 0){
        printf("Es un numero par\n");
    }
    else{
        printf("No es un numero par\n");
    }
    return 0;
}
