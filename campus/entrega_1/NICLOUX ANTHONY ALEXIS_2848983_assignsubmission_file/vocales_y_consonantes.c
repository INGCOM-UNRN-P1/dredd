/*
Ejercicio 1.6 - Vocales y Consonantes
Leé un carácter y determiná si es vocal, consonante, dígito u otro símbolo.

------------------

Anthony Alexis Nicloux
alex44523
*/

#include <stdio.h>
#include <ctype.h>

// ¡IMPORTANTE! solo funciona con 1 solo caracter 
int main(){
    char texto = '0';
    scanf ("%c", &texto);
    switch (texto){
        case 'a':
            printf ("Es la vocal \"a\" miniscula");
            break;
        case 'e':
            printf ("Es la vocal \"e\" miniscula");
            break;
        case 'i':
            printf ("Es la vocal \"i\" miniscula");
            break;
        case 'o':
            printf ("Es la vocal \"o\" miniscula");
            break;
        case 'u':
            printf ("Es la vocal \"u\" miniscula");
            break;
        case 'A':
            printf ("Es la vocal \"A\" miniscula");
            break;
        case 'E':
            printf ("Es la vocal \"E\" miniscula");
            break;
        case 'I':
            printf ("Es la vocal \"I\" miniscula");
            break;
        case 'O':
            printf ("Es la vocal \"O\" miniscula");
            break;
        case 'U':
            printf ("Es la vocal \"U\" miniscula");
            break;
        default:
            // 'isupper' verifica si es mayuscula de la libreria <ctype.h>
            if (isupper(texto)){
                printf ("Es la consonante \"%c\" mayuscula", texto);
            // 'islower' verifica si es minuscula
            }else if (islower(texto)){
                printf ("Es la consonante \"%c\" minuscula", texto);
            }else if (isdigit(texto)){
                printf ("Es el digito \"%c\"", texto);
            }else {
                printf ("Es el caracter especial \"%c\"", texto);
            }
    }
    return 0;
}