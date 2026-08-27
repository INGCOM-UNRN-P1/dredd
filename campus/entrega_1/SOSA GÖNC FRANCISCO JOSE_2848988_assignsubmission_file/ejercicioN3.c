/*
Ejercicio 3 - Par o Impar
------------------
Francisco Sosa Gonc
sancocho192
*/
#include <stdio.h>
int main() {
int N;
printf("ingrese numero:");
scanf("%d" ,&N);
if (N%2==0){
    printf("el numero es par");
} else{
    printf("el numero es impar");
}
return 0;

}