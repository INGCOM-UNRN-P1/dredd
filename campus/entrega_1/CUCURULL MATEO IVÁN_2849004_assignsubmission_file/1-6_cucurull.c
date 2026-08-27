/*
Ejercicio 1.6 - Secuencia ascendente
"Aca se muestra una cadena de números ascendente desde un numero n definido por el usuario 
hasta un numero m escaneado de la consola"
--------------------
Nombre y Apellido: Mateo Cucurull
Usuario en GitHub: MattCucurull
*/
#include <stdio.h>

int main() {
    int n = 0;
    int m = 0;

    printf("Ingrese el limite inferior 'n' del intervalo (m, n]");
    scanf("%d", &n);
    printf("Ingrese el limite superior 'm' del intervalo (m, n]");
    scanf("%d", &m);
    
    for(int i = n; i < m; i = i + 1){
        printf("%d\n", i);
    }
}