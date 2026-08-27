/*
Ejercicio 2 - Secuencia Ascendente
------------------
Francisco Sosa Gonc
sancocho192
*/
#include <stdio.h>
int main() {
    int n;
    int m;
printf("ingrese el primer numero:");
scanf("%d",&n);
printf("ingrese el ultimo numero");
scanf("%d",&m);

printf("secuencia de numeros entre el primero y el ultimo:\n");
for (int i=n; i<m; i++){
    printf("%d",i);
}
printf("\n");
return 0;

}