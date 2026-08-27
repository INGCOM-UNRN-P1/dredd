/*
Ejercicio 1.6 - Vocales y Consonantes ⭐⭐⭐☆☆
Leé un carácter y determiná si es vocal, consonante,
dígito u otro símbolo.
-----------------
Nombre y Apellido: Lautaro Costantini
Usuario Github: L-Ezql
*/

#include <stdio.h>
#include <ctype.h>

int main ()
{
    char caracter =' ';
    printf("Ingresar un caracter: ");
    scanf(" %c", &caracter);
    
    if (isdigit(caracter))
    {
        printf("'%c' es un DIGITO\n", caracter);
        return 0;
    }
    if (isalpha(caracter))
    {
        switch (tolower(caracter))      //  La IA me sugirió como gestionar las mayúsculas/minúsculas
        {
            case 'a':
            case 'e':
            case 'i':
            case 'o':
            case 'u':
                printf("'%c' es una VOCAL\n", caracter);
                break;
            default:
                printf("'%c' es una CONSONANTE\n", caracter);
                break;
        }
        return 0;
    }
    printf("'%c' es un SIMBOLO\n", caracter);
    return 0;
}