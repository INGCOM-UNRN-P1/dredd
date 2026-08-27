/*
Ejercicio 1.6 – Vocales y consonantes 
Leé un carácter y determiná si es vocal, consonante, dígito u otro símbolo.
-----------------
Iñaki Montes
iniaki12
*/

#include <stdio.h>
#include <ctype.h>

int main()
{
    char caracter = '\0';
    printf("por favor, ingrese un caracter: ");
    scanf(" %c", &caracter);
    if (isalpha(caracter))
    {
        switch (caracter)
        {
        case 'a': case 'e': case 'i': case 'o': case 'u':
        case 'A': case 'E': case 'I': case 'O': case 'U':
            printf("el caracter %c es una vocal \n", caracter);
            break;
        
        default:
            printf("el caracter %c es una consonante \n", caracter);
            break;
        }
    }
    else if (isdigit(caracter))
    {
        printf("el caracter %c es un digito\n", caracter);
    }
        else
        {
            printf("el caracter %c es otra cosa\n", caracter);
        }
    return 0;
}
