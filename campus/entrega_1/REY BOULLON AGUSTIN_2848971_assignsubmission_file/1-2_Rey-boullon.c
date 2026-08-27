#include <stdio.h>
int main(void){
int m = 0;
int n = 0;
int i = 0;
printf("Secuencia ascendente. Ingrese el primer numero: \n");
scanf("%d", &n);
printf("Ingrese el segundo numero :\n");
scanf("%d", &m);
 
for (i=n; i<m; i++) {
printf("%d ", i);
}
return 0;
}