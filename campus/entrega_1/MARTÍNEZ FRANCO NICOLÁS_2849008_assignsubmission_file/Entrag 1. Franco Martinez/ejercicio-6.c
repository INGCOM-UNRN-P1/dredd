/*
Ejercicio 6.1 – Vocales y Consonantes
Leé un carácter y determiná si es vocal, consonante, dígito u otro símbolo.
-----------------
Franco Martinez
Usuario Github : Fr4ncos7
*/

#include <stdio.h>
#include <ctype.h>

int main() 
{
    char caracter;


    printf("ingrese una letra: \n");
    scanf("%c", &caracter);

    if (isalpha(caracter))
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
            printf("%c, Es una vocal", caracter);
            break;
    
        default:
            printf("%c, Es una consonante", caracter);
            break;
        }
    }
    else if (isdigit(caracter))
    {
        printf("Eso es un digito. \n");
    }
    else
    {
        printf("Es un simbolo. \n");
    }
    

    return 0;
}