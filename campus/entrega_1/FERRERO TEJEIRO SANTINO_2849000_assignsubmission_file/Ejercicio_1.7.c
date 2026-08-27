//Ejercicio 7 - Conversor de calificaciones
//Convertí entre diferentes sistemas de calificación: numérica (0-10), letra (A-F), porcentaje (0-100).
#include<stdio.h>
#include <ctype.h>

int main(){

    int opcion = 0;

    printf("Que tipo de sistema desea utilizar:\n opcion = 0 sistema numerico (0.0 - 10.0).\n opcion = 1 sistema letras (F - A). \n opcion = 2 sistema de porcentaje (0 - 100).\n");
    scanf("%d", &opcion);

    switch (opcion)
    {
    case 0:{
        float num;
        float numporciento = 0.0;
        printf("Ingrese una calificacion. \n");
        scanf("%f", &num);

        if (num < 0.0 || num > 100.0)
        {
            printf("Error: Nota invalida (0.0 - 10.0)");
        }
        else{
            numporciento = num * 10;

            char letra;
            if (num >= 9.0)
            {
                letra= 'A';
            } else if (num >= 8.0)
            {
                letra = 'B';
            } else if (num >= 7.0)
            {
                letra = 'C';
            } else if (num >= 6.0)
            {
                letra = 'D';
            } else
            {
                letra = 'F';
            }
            
            printf("\n --- REULTADOS --- \n");
            printf("Porcentaje: %.1f%%\n", numporciento);
            printf("Letra: %c\n", letra);
        }
        break;
     }
    case 1:{
        char letra;
        float numero;
        float porcentaje;

        printf("Ingrese una calificacion. \n");
        scanf(" %c", &letra);
        if (islower(letra))
        {
            printf("Error: Nota invalida, debe ser en mayusculas (F - A). \n");
        } else{
            if (letra == 'A'){
                numero = 10.0;
                porcentaje = 100.0;
            }
            else if (letra == 'B'){
                numero = 8.5;
                porcentaje = 85.0;
            }
            else if (letra == 'C'){
                numero = 7.5;
                porcentaje = 75.0;
            }
            else if (letra == 'D'){
                numero = 6.5;
                porcentaje = 65.0; 
            }
            else if (letra == 'F'){
                numero = 5.0;
                porcentaje = 50.0;
            }
            else{
                printf("Error: letra invalida.\n");
            }
            
             printf("\n --- REULTADOS --- \n");
            printf("Porcentaje: %.1f%%\n", porcentaje);
            printf("Numero: %.1f\n", numero);
        }
        break;
    }
    case 2:{
        float porcentaje;
        char letra;

        printf("Ingrese una calificacion. \n");
        scanf("%f", &porcentaje);
        if (porcentaje < 0 || porcentaje > 100){
            printf("Error: Nota invalida (0.0 - 100.0)");
        }
        else{
            float numero;

            numero = porcentaje / 10;

             if (porcentaje >= 90.0)
             {
                letra = 'A';
             }
             else if (porcentaje >= 80.0)
             {
                letra = 'B';
             }
             else if(porcentaje >= 70)
             {
                letra = 'C';
             }
             else if (porcentaje >= 60.0)
             {
                letra = 'D';
             }
             else
             {
                letra = 'F';
             }
            printf("\n --- REULTADOS --- \n");
            printf("Nota numerica: %.1f\n", numero);
            printf("Numero: %c\n", letra);
        }
        break;
     }
        
    
    default:
    {
        printf("Error: Opcion incorrecta (0 - 2).\n");
    }
        break;
    }
    return 0;
}//main
/*
Nombre y apellido: Ferrero Santino
Usuario de Github: santinof256
*/