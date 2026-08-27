/*
Ejercicio 5 - Contador de Dígitos
Crear una función que reciba un número entero y devuelva la cantidad de dígitos que lo componen.
-----------------
Maximiliano Vargas
vsmaxy
*/

#include <stdio.h>

int contador_dig(int num)
{
    int contador = 0;

    if(num==0)
    {
        contador = 1;
    }
    else
    {
        while(num != 0)
        {
            num = num/10;
            contador++;
        }
    }
    return contador;
}
int main(void)
{
    int numero = 0;
    int contador = 0;

    printf("Ingrese un numero: ");
    scanf("%d", &numero);

    contador = contador_dig(numero);
    printf("%d tiene %d digitos",numero,contador);
    return 0;
}