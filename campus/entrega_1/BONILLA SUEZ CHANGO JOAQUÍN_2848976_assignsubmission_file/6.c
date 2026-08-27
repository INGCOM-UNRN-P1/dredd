/*
Ejercicio 6 - Vocales y Consonantes

Leé un carácter y determiná si es vocal, consonante, dígito u otro símbolo.
-----------------
Chango Joaquin Bonilla Suez
https://github.com/ysin-war
*/

#include <stdio.h>
#include <ctype.h>

int main(){
    char c = 0;
    printf("Por favor ingrese un caracter\n");
    scanf("%c", &c);
    if (isalpha(c)){
        switch(c){
            case (65):
                printf("%c es vocal\n", c);
            break;
            case (97):
                printf("%c es vocal\n", c);
            break;
            case (69):
                printf("%c es vocal\n", c);
            break;
            case (101):
                printf("%c es vocal\n", c);
            break;
            case (73):
                printf("%c es vocal\n", c);
            break;
            case (105):
                printf("%c es vocal\n", c);
            break;
            case (79):
                printf("%c es vocal\n", c);
            break;
            case (111):
                printf("%c es vocal\n", c);
            break;
            case (85):
                printf("%c es vocal\n", c);
            break;
            case (117):
                printf("%c es vocal\n", c);
            break;
            default:
                printf("%c es consonante\n", c);
        }
    }
    else if (isdigit(c)){
        printf("%c es digito\n", c);
    }
    else{
        printf("%c no es alfanumerico\n", c);
    }
    printf("%c es %d\n", c, c);
    return 0;
}

