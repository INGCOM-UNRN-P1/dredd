/*
Ejercicio 5 - Contador de Dígitos

Crear una función que reciba un número entero y devuelva la cantidad de dígitos
que lo componen.
-----------------
Chango Joaquin Bonilla Suez
https://github.com/ysin-war
*/

#include <stdio.h>

int main(){
    // Al ser 'n' de tipo int la funcion contarDigitos() solo puede contar hasta
    // ~10 digitos
    int n = 0;
    printf("Por favor ingrede un numero\n");
    scanf("%d", &n);
    printf("digitos: %d\n", contarDigitos(n));
    return 0;
}

int contarDigitos(int n){
    int digitos = 0;
    if (n == 0){
        return 0;
    }
    while (n > 0){
        digitos = digitos + 1;
        n = n / 10;
        printf("%d\n", n);
    }
    return digitos;
}
