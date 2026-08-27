/*
Ejercicio 1.37 - Contador de Dígitos
"En este ejercicio se van a contar la cantidad de números que hay en un digito dado por el usuario
 esto implica dividirlo sucesivamente por 10 hasta llegar a un mínimo irreducible: 0.
 y mostrar la cantidad de iterciones"

Nombre y Apellido: Mateo Cucurull
Usuario de Github: MattCucurull
*/
#include <stdio.h>
#include <stdlib.h> /*Necesaria para usar la función de valor absoluto en C*/

int main(){
    int entrada_del_usuario = 0; 
    int cantidad_de_digitos = 0;
    int numero_absoluto = 0; 

    printf("Ingrese un numero para contar su cantidad de digitos: \n");
    scanf("%d", &entrada_del_usuario);

    /*Sacar el valor absoluto de la entrada del usuario permite que el codigo funcione para todos los enteros*/
    numero_absoluto = abs(entrada_del_usuario); 
    

    if (numero_absoluto > 0){
        while(numero_absoluto > 0){
            cantidad_de_digitos = cantidad_de_digitos + 1;
            numero_absoluto = numero_absoluto / 10;
        }
        printf("Tu numero tiene %d digitos", cantidad_de_digitos);        
    }
    else{
        printf("Tu numero es 0 por lo que no se le pueden contar la cantidad de digitos");
    }
    return 0;
}