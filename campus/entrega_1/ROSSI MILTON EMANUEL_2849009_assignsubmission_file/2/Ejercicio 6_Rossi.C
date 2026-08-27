/**
Ejercicio 6 - Vocales y consonantes
Leé un carácter y determiná si es vocal, consonante, dígito u otro símbolo..
-----------------
Nombre y Apellido:Milton Rossi
Usuario Github: milton1000
*/

#include<stdio.h>
#include<ctype.h>

int main() {
    
    char caracter;
    int  vocal = 0;

    printf("ingrese un caracter:");
    scanf("%c",&caracter);
            
    if(isdigit(caracter)) {
                    
        printf("Es un digito.\n");
    }
                
    else if (isalpha(caracter)) {
                    
        switch (caracter) {
            case 'a':
            case 'e':
            case 'i':
            case 'o':
            case 'u':                 
            
            printf("Es una vocal minuscula\n");
            vocal = 1;
        
            break;

            case 'A':
            case 'E':
            case 'I':
            case 'O':
            case 'U': 
                                
            printf("Es una vocal mayuscula\n");
            vocal = 1;
            
            break;
        }
                
        if((vocal != 1) && ((caracter >= 'a') && (caracter <= 'z'))) {

            printf("Es una consonante minuscula\n");
        }
                
        else if ((vocal != 1) && (caracter >= 'A') && (caracter <= 'Z')) {
            
            printf("Es una consonante mayuscula\n");
        }
    }
                
    else { 
        
    printf("Es otro simbolo.\n"); 
    }

return 0;
}



