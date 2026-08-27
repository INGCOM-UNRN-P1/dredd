// Ejercicio 6 - Vocales y Consonantes
//Leé un carácter y determiná si es vocal, consonante, dígito u otro símbolo.

#include<stdio.h>
#include<ctype.h>
#include<stdlib.h>

int main(){

    char caracter;

    printf("Ingrese un caracter: \n");
    scanf("%c", &caracter);

    if(isalpha(caracter)){
        if (isupper(caracter))
        {
            switch (caracter)
            {
            case 'A': {
                printf("Es una vocal mayuscula.\n", caracter);
                break;
                }
            case'E': {
                printf("Es una vocal mayuscula.\n", caracter);
                break;
                }
            case 'I': {
                printf("Es una vocal mayuscula.\n", caracter);
                break;
                }
            case 'O': {
                printf("Es una vocal mayuscula.\n", caracter);
                break;
                }
            case 'U': {
                printf("Es una vocal mayuscula.\n",caracter);
                break;
                }
            default: {
                printf("Es una consonante mayuscula. \n", caracter);
                break;
                }
            }
        }
        else if(islower){

         switch (caracter){
            case 'a': {
                printf("Es una vocal minuscula.\n",caracter);
                break;
                }
            case'e': {
                printf("Es una vocal minuscula.\n",caracter);
                break;
                }
            case 'i': {
                printf("Es una vocal minuscula.\n",caracter);
                break;
                }
            case 'o': {
                printf("Es una vocal minuscula.\n", caracter);
                break;
                }
            case 'u': {
                printf("Es una vocal minuscula.\n", caracter);
                break;
                }
            default: {
                printf("Es una consonante minuscula. \n", caracter);
                break;
                }
            }
        }
    }
    else if(isdigit(caracter)){
        printf("Es un numero.\n", caracter);
    }
    else{
        printf("Es un simbolo.\n", caracter);
    }

    return 0;

}//main 

/* 
Nombre y apellido: Ferrero Santino.
Usuario de Github: santinof256.
*/