/*
Ejercicio 1.3 - Par o Impar
Este es un ejercicio fundamental de lógica
condicional. El programa debe solicitar un
número entero al usuario y determinar si
es par (divisible por 2) o impar.

-------------------

Anthony Alexis Nicloux
alex44523
*/

#include <stdio.h>

int main(){
    int numero = 0;
    scanf ("%d", &numero);
    printf ("El numero %d ", numero);
    if ((numero % 2) == 0){
        printf ("es par\n");
    } else {
        printf ("es impar\n");
    }
    return 0;
}