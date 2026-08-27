/*
Ejercicio 3 – Par o Impar
Este es un ejercicio fundamental de lógica condicional. 
El programa debe solicitar un número entero al usuario y determinar si es par (divisible por 2) o impar.

-----------------
Nombre y Apellido: Milton Rossi
Usuario Github: milton1000
*/
#include <stdio.h>
int main (){

    int numero=0;

        printf("Ingrese un numero:");
        scanf("%d",&numero);

            if(numero %2 == 0)
            {
                printf("El numero %d es par", numero);
            }
            else 
            {
                printf("El numero %d  es impar",numero);
            }  
return 0;
}
