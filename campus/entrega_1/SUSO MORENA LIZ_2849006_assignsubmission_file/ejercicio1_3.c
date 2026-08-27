/*
Ejercicio 3 - Par o Impar
Este es un ejercicio fundamental de lógica condicional. El programa debe solicitar 
un número entero al usuario y determinar si es par (divisible por 2) o impar.
-----------------
Morena Suso
MorenaSuso
*/

// main
#include <stdio.h>

int main()
{
    int n =0;
    printf("ingrese un valor: \n");
    scanf("%d", &n);

    if (n % 2 == 00)
    {
        printf("%d es par \n", n);
    }
    else
     {
        printf("%d es impar", n);
     }
     
return 0;
}