/*
Ejercicio 6 - Vocales y Consonantes
Leé un carácter y determiná si es vocal, consonante, dígito u otro símbolo.
-----------------
Maximiliano Vargas
vsmaxy
*/
#include <stdio.h>
#include <ctype.h>

int main(void)
{
    char caracter = '\0';

    printf("Ingrese un caracter: ");
    scanf(" %c", &caracter);

    switch(caracter)
    {
        case 'a':
        case 'A':
        case 'e':
        case 'E':
        case 'i':
        case 'I':
        case 'o':
        case 'O':
        case 'u':
        case 'U':
            printf("Es una vocal\n");
            break;

        default:
            if(isalpha(caracter))
            {
                printf("Es una consonante\n");
            }
            else if (isdigit(caracter))
            {
                printf("Es un numero\n");
            }
            else
            {
                printf("Es otro simbolo\n");
            }
            break;
    }    

    return 0;
}