// Ejercicio 3 - Par o Impar
//Este es un ejercicio fundamental de lógica condicional. El programa debe solicitar un número entero al usuario y determinar si es par (divisible por 2) o impar.

#include<stdio.h>
int main(){
    int num = 0;

    printf("Ingrese un numero entero: \n");
    scanf("%d", &num);

    if(num % 2 == 0){
        printf("El numero es par\n");
    }
    else{
        printf("El nuemro es impar\n");
    }
    return 0;
} //main
/*
Nombre y apelledo: Ferrero Santino
Usuario de Github: santinof256
*/