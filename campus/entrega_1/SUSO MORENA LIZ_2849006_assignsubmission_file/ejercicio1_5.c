/*
Ejercicio 5 - Contador de Dígitos 
Crear una función que reciba un número entero y 
devuelva la cantidad de dígitos que lo componen.
-----------------
Morena Suso
MorenaSuso
*/

// main
#include <stdio.h>

 int main()
 {
    int n = 0;
    int digito = 0;
    int contador = 0;

   printf("Ingrese el numero: \n");
   scanf("%d", &n);

   if(n == 0)
   {
    printf("Digitos: 1\n");
   }
   else
   {
        while(n > 0)
        {
            digito = n % 10;
            contador = contador + 1;
            n = n / 10 ;
        }
        printf("Digitos: %d\n", contador);
    }
   
    return 0 ;
 }