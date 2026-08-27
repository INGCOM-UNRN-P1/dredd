
/*
Ejercicio 4 - Invertir un Número Entero 
Implementar una función que tome un número entero y
 devuelva otro número con los dígitos en orden inverso.
-----------------
Morena Suso
MorenaSuso
*/

// main
 #include <stdio.h>

 int main()
 {
    int n = 0;
    int invertido = 0;
    int digito = 0;

   printf("Ingrese el numero a invertir: \n");
   scanf("%d", &n);

   if(n != 0)
   {
      while(n > 0)
      {
         digito = n % 10;
         invertido = invertido * 10 + digito;
         n = n / 10;
      }
       printf("Numero invertido: %d\n", invertido);
   }
   else
   {
      printf("numero invalido\n");
   }   

    return 0 ;


 }