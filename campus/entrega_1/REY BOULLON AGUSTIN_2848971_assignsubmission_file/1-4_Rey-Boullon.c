#include <stdio.h>
int main (void){
int invertido = 0;
int numero = 0;
int digito = 0;

printf("Ingrese el numero a invertir\n");
scanf("%d",&numero);

    while (numero !=0) {
        digito = numero % 10;
        invertido = (invertido *10 ) + digito;
        numero = numero / 10;
    }
    printf("El numero invertido es %d", invertido);
return 0;
}