/*
Ejercicio 4 – Invertir un Número Entero
Implementar una función que tome un número entero y devuelva otro número con los dígitos en orden inverso.

-----------------
Nombre y Apellido: Milton Rossi
Usuario Github: milton1000
*/
#include <stdio.h>
int main (){

    int numero=0;
    int invertido=0;
    int digito=0;

        printf("Ingrese un numero:");
        scanf("%d",&numero);
            
            while(numero>0)
            {
                digito= numero % 10;
                invertido=(invertido*10) + digito;
                numero=numero/10;
            }
                printf("El numero invertido es: %d",invertido);
return 0;
}
