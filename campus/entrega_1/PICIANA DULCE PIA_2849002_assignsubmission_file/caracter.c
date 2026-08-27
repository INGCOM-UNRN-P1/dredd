/*
Ejercicio 6 – Vocales y consonantes
Leer un carácter y determinar si es vocal, consonante, dígito u otro símbolo
-----------------
Dulce Piciana
dulcepiciana
*/
#include<stdio.h>
int main()
{
char caracter= '\0';
printf("Ingrese su carácter: ");
scanf(" %c",&caracter);
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
        printf("Es una vocal");
        break;
    case '0':
    case '1':
    case '2':
    case '3':
    case '4':
    case '5':
    case '6':
    case '7':
    case '8':
    case '9':
        printf("Es un dígito numérico");
        break;
    
    default:
        if (caracter >= 'a' && caracter <= 'z')
        {
            printf("Es una consonante");
        }
        else if (caracter >= 'A' && caracter <= 'Z')
        {
            printf("Es una consonante");
        }
        else{
            printf("Es un símbolo);");
        }
        break;
} 
}

