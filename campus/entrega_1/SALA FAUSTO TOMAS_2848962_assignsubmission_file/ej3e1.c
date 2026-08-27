/*
Ejercicio 1.3 – Par o Impar
Este es un ejercicio fundamental de lógica condicional. 
El programa debe solicitar un número entero al usuario 
y determinar si es par (divisible por 2) o impar.
-----------------
Nombre y Apellido: Fasuto Tomas Sala
Usuario Github: tomassala1
*/

// main
#include <stdio.h>

int main(){
    int n;

    printf("Ingrese un numero para saber si es par: ");
    scanf("%d", &n);

    if (n % 2 == 0){
        printf("El numero es par");
    }   else {
        printf("El numero es impar");
    }
    

    return 0;
}