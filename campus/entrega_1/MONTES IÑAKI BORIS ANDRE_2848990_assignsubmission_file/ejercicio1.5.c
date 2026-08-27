/*
Ejercicio 1.5 – Contador de digitos
Crear una función que reciba un número entero y devuelva la cantidad de dígitos que lo componen.
-----------------
Iñaki Montes
iniaki12
*/

#include <stdio.h>
int contadorDigitos(int digitos)
{
    int contador = 0;
    if (digitos == 0)
    {
        return 1;
    }
    while (digitos > 0)
    {
        digitos /= 10;
        contador++;
    }
    return contador;
}
int main()
{
    int numero;
    printf("ingresar un numero: ");
    scanf("%d", &numero);
    if (numero < 0)
    {
        printf("el numero debe ser entero positivo");
        return 1;
    }
    printf("la cantidad de digitos en el numero %d es: %d\n", numero, contadorDigitos(numero));
    return 0;
}