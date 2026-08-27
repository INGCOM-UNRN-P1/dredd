/*
Ejercicio 6 - Vocales y Consonantes 
Leé un carácter y determiná si es vocal, consonante, 
dígito u otro símbolo.
-----------------
Morena Suso
MorenaSuso
*/

// main
#include <stdio.h>
#include <ctype.h>

int main()
{
    char caracter;
    printf("Ingrse un caracter: \n");
    scanf("%c", &caracter);

    if(isalpha(caracter))
    {
        switch (caracter)
         {
             case 'a':
             case 'e':
             case 'i':
             case 'o':
             case 'u':
             case 'A':
             case 'E':
             case 'I':
             case 'O':
             case 'U':
            printf("Es vocal\n");
            break;

            default:
            printf("Es consonante\n");
         }
    }
    else if(isdigit(caracter))
    {
        printf("Es un digito\n");
    }
    else
    {
        printf("Es un caracter especial\n");
    }

    return 0;
}