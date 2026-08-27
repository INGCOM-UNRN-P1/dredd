/*
 * Ejercicio 1.6 - Vocales y Consonantes.
 * Leé un carácter y determiná si es vocal, consonante, dígito u otro símbolo.
 *
 * Nombre y Apellido: Nehuen Schneebeli.
 * github: NehuenSch.
 */

#include <stdio.h>
#include <ctype.h>


int main()
{
   char simbolo = '\0';
   
   printf("Ingrese un sombolo: ");
   scanf("%c", &simbolo);

  
    switch(simbolo)
    {
	    case 'A': case 'a': case 'E': case 'e': case 'I': case 'i': case 'O': case 'o': case 'U': case 'u':
	    printf("Es una vocal!\n");
	    break;
      
        default:
	    if(isdigit(simbolo))
	    {
	        printf("Es un simbolo no perteneciente al ABC...\n");
	    } else {
	        printf("Es una consonante!\n");
	    }
    	break;
    
    }

    return 0;
}
