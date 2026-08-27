/*
 * Ejercicio 1.4 - Invertir numero.
 * Escrbir un programa que al cargar un numero entero lo devuelva espejado.
 * Este ejercicio nos permite desarrollar las habilidades basicas para dominar el lenguaje C.
 *
 * ---------------
 *  Nombre y Apellido: Nehuen Schneebeli.
 *  Github: NehuenSch.
 */

#include <stdio.h>

int main()
{
    int num_original = 0;
    int resto = 0;
    
    printf("Ingrese un numero perteneciente a los reales: ");
    scanf("%d", &num_original);
 

    while(num_original>0)
    {
	resto = num_original % 10;
        num_original = num_original / 10;
	printf("%d", resto);
    
    }
    printf("\n");
    return 0;
}
