/*
Ejercicio 2.12 - Vocales y Consonantes
"En este ejercicio se va a tomar un caracter por scanf y se va a verificar si
este es un caracter alfanúmerico, un digito o una letra y en este último
se verifica se esta es una vocal o una consonante"

---------------
Nombre y Apellido: Mateo Cucurull
Usuario de GitHub: MattCucurull
*/

#include <stdio.h>
#include <ctype.h> /* Se importa la libreria ctype para usar la función isalpha() y isdigit()*/

int main(){
    char entrada_del_usuario = '0';
    char valor_en_minusculas = 'a';

    printf("Ingrese un caracter para conocer su tipo\n");
    scanf("%c", &entrada_del_usuario);

    if (isdigit(entrada_del_usuario)){
        printf("Tu caracter: '%c' es un digito\n", entrada_del_usuario);
    }
    else if(isalpha(entrada_del_usuario)){
        valor_en_minusculas = tolower(entrada_del_usuario);
        switch (valor_en_minusculas)
        {
        case 'a': case 'e': case 'i': case 'o': case 'u':
            printf("Tu letra: '%c' es una vocal\n", entrada_del_usuario);
            break;

        /* No tuve en cuenta la letra ñ porque no es compatible con mi compilador*/    
        case 'b': case 'c': case 'd': case 'f': case 'g':
        case 'h': case 'j': case 'k': case 'l': case 'm':
        case 'n': case 'p': case 'q': case 'r': case 's':
        case 't': case 'v': case 'w': case 'x': case 'y':
        case 'z':
            printf("Tu letra: '%c' es una consonante\n", entrada_del_usuario);
            break;  

        default:
            printf("No pudimos reconocer tu letra '%c' como vocal o consonante\n", entrada_del_usuario);
            break;
        }
    }
    else{
        printf("Tu caracter es un simbolo\n");
    }

    return 0;
}