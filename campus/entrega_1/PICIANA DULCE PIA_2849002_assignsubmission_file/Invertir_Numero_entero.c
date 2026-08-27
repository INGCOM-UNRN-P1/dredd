/*
Ejercicio 4 – Invertir un Número entero
Implementar funcion que tome un numero entero y devuelva 
otro número con los dígitos en orden inverso
-----------------
Dulce Piciana
dulcepiciana
*/
#include<stdio.h>
int main()
{
    int numero=0;
    int invertido=0; 
    int digito=0;   //Asi el primer resultado sea el digito tal cual y no afecta
    printf("Ingrese número entero:\n");
    scanf("%d",&numero);
    printf("numero ingresado es: %d\n",numero);
    while (numero != 0)
    {
        digito = numero % 10  ;    //Obtengo ultimo digito
        invertido =(invertido*10) + digito;//Aca voy guardando mi nuevo numero
        numero = (numero / 10);//Aca elimino ultimo digito del numero original
        printf("Numero invertido es: %d\n",invertido);
    }
    return invertido;

}