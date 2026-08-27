#include <stdio.h> 
/*
 * Escribir un programa que muetre el recorrido desde n inclusive hasta
 * terminar uno antes de m.
 * El ejercicio permitira los primeros asercamientos a los lazos.
 *
 * Nombre y apellido: Nehuen Schneebeli.
 * github: NehuenSch.
 */

int main()
{
    int n = 0;
    int m = 0;
    
    int num_menor = 0;
    int num_mayor = 0;
    
    printf("Se le pedira que ingrese dos valores distintos para demostrar una secuencia ascendete en los valores.\nLos valores ingresados deben de pertenecer al conjunto numerico de los ENTEROS.\n");

    printf("Ingrese un numero para el parametro: ");
    scanf("%d", &n);

    printf("Ingrese un numero para el parametro: ");
    scanf("%d", &m);

    if(n < m)
    {
        num_menor = n;
        num_mayor = m;
    }
    else if(n == m)
    {
        printf("Los numeros son iguales, intentelo de nuervo mas tarde.\n");
    }
    else 
    {
        num_menor = m;
	num_mayor = n;
    }
    while(num_menor < num_mayor)
    {
        printf("El numero es: %d\n", num_menor);
	num_menor = num_menor + 1;
    }

    return 0;
}
