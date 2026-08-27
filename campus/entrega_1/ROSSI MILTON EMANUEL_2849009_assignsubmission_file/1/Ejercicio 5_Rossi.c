/**
Ejercicio 5 - Contador de Dígitos
Crear una función que reciba un número entero y devuelva la cantidad de dígitos que lo componen.
-----------------
Nombre y Apellido:Milton Rossi
Usuario Github: milton1000
*/
#include<stdio.h>
int main (){
    
    int numero=0;
    int cant_digitos=0;

        printf("ingrese un numero:");
        scanf("%d",&numero);

            if(numero!=0)
            {
                while(numero>0)
                {
                    numero=numero/10;
                    cant_digitos=cant_digitos+1;  
                }
                    if(cant_digitos>1)
                    {
                        printf("El numero tiene %d digitos", cant_digitos);
                    }

                    else
                    {   
                    printf("El numero tiene %d digito", cant_digitos);
                    }
            }
            
            else{
                printf("El numero 0 tiene un digito");
                } 
return 0;       
}








