/*
Ejercicio 3 – Par o Impar
Este es un ejercicio fundamental de lógica condicional. 
El programa debe solicitar un número entero al usuario y determinar si es par (divisible por 2) o impar.

-----------------
Nombre y Apellido: Milton Rossi
Usuario Github: milton1000
*/
#include <stdio.h>

int main () {

    int numero_entero = 0;

    printf("Ingrese un numero:");
    scanf("%d",&numero_entero);

    if(numero_entero % 2 == 0) {
                
        printf("El numero %d es par", numero_entero);
            
    }
    
    else {

        printf("El numero %d  es impar",numero_entero);
    
    }  

    return 0;
}
