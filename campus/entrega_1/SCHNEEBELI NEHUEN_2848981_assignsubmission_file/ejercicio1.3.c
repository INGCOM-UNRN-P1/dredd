#include <stdio.h>

/*
 * Ejercicio 1.3 - Par o Impar.
 *
 * Se busca imprimir si un numero ingresado es par o impar.
 * Este ejercicio nos permitira desarrollar la logica.
 *
 * Nombre y Apellido: Nehuen Schneebeli.
 * Github: NehuenSch.
 */

int main()
{

    int resto = 0;
    int numero = 0;
    printf("Ingrese el numero que le gustaria averiguar si es positivo o negativo.\n");
    scanf("%d", &numero);


    resto = numero %2;

    if(resto == 0)
    {
        printf("El numero ingresado es par\n");
    }
    else
    {
        printf("El numero ingresado es impar\n");
    }

    
    return 0;
}
