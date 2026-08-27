/*
Ejercicio 6 – Vocales y Consonantes 
Leé un carácter y determiná si es vocal, consonante, dígito u otro símbolo.
-----------------
Facundo Argerich
Github: ArgerichFacu
*/

#include <stdio.h>
#include <ctype.h>

int main ()
{
    unsigned char valor;

    printf("Ingrese cualquier valor: \n");
    scanf("%c", &valor);

    if (isalpha(valor))
    {
        if (isupper(valor))
        {
            if (valor == 'A' || valor == 'E' || valor == 'I' || valor == 'O' || valor == 'U')
            {
                printf("%c es una vocal mayuscula.", valor);
            }
            else
            {
                printf("%c es una consonante mayuscula.", valor);
            }
        }
        else if (islower(valor))
        {
            if (valor == 'a' || valor == 'e' || valor == 'i' || valor == 'o' || valor == 'u')
            {
                printf("%c es una vocal minuscula.", valor);
            }
            else
            {
                printf("%c es una consonante minuscula.", valor);
            }
        }
    }
    else if (isdigit(valor))
    {
        printf("%c es un digito.", valor);
    }
    else
    {
        printf("%c caracter especial.", valor);
    }
    return 0;
}