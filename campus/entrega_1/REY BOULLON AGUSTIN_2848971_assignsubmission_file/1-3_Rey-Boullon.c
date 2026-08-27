#include <stdio.h>
int main (void){
int n = 0;
printf("Ingrese un numero y la consola determinara si es par o impar.\n");
scanf("%d",&n);
    if(n%2==0) {
        printf("Su numero es par.\n");
    } else{
        printf("Su numero es impar.\n");
    }
return 0;    
}