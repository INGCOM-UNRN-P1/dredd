/*
Ejercicio 5 – Contador de Dígitos
Crear función que reciba un número entero y devuelva la cantidad 
de dígitos que lo componen
-----------------
Dulce Piciana
dulcepiciana
*/
#include<stdio.h>
int main()
{
    int numero=0;
    int contador = 0;
    printf("Ingrese número entero:\n",numero);
    scanf("%d",&numero);
    if(numero==0)
    {
        return 1;
    }
    contador = 0;
    while ( numero>0)
    {
        numero = (numero / 10);
        contador = contador + 1;
        printf("La cantidad de digitos es:%d\n",contador);
    }
    return contador;
}