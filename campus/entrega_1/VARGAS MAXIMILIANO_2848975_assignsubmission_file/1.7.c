/*
Ejercicio 7 - Conversor de Calificaciones
Convertí entre diferentes sistemas de calificación: numérica (0-10), letra (A-F), porcentaje (0-100).
Numérica 0-10  <->  Porcentaje 0-100
       9-10    -> A
       8-8.9   -> B
       7-7.9   -> C
       6-6.9   -> D
       0-5.9   -> F
-----------------
Maximiliano Vargas
vsmaxy
*/
#include <stdio.h>

char numerica_a_letra(float num)
{
    char letra = 'F';

    if(num >= 9)
    {
        letra = 'A';
    }
    else if(num >= 8)
    {
        letra = 'B';
    }
    else if(num >= 7)
    {
        letra = 'C';
    }
    else if(num >= 6)
    {
        letra = 'D';
    }
    return letra;
}

float numerica_a_porcentaje(float num)
{
    int porcentaje = num *10;
    return porcentaje;
}

float porcentaje_a_numerica(float porcentaje)
{
    porcentaje = porcentaje / 10;
    return porcentaje;
}
char porcentaje_a_letra(float porcentaje)
{
    char letra = 'F';

    if( porcentaje >= 90){
        letra = 'A';
    }
    else if(porcentaje >= 80)
    {
        letra = 'B';
    }
    else if(porcentaje >= 70)
    {
        letra = 'C';
    }
    else if(porcentaje >= 60)
    {
        letra = 'D';
    }
    return letra; 
}
int main(void)
{
    int opcion = 0;
    float num = 0;
    float porcentaje = 0;
    char letra = '\0';
    float nota = 0;
    char notaL = '\0'; 


    printf("OPCIONES:\n");
    printf("1. Numerica a Letra\n");
    printf("2. Numerica a Porcentaje\n");
    printf("3. Porcentaje a Numerica\n");
    printf("4. Porcentaje a Letra\n");
    printf("Ingrese una opcion: ");
    scanf("%d",&opcion);

    switch (opcion)
    {
    case 1:
        printf("Ingrese nota entre 0-10: ");
        scanf("%f", &num);
        notaL = numerica_a_letra(num);
        printf("%.2f = %c",num,notaL);
        break;
    case 2:
        printf("Ingrese una nota entre 0-10: ");
        scanf("%f", &num);
        porcentaje = numerica_a_porcentaje(num);
        printf("%.2f = %.2f",num,porcentaje);
        break;
    case 3:
        printf("Ingrese porcentaje entre 0-100: ");
        scanf("%f",&porcentaje);
        nota = porcentaje_a_numerica(porcentaje);
        printf("%.2f = %.2f",porcentaje,nota);
        break;
    case 4:
        printf("Ingrese porcentaje entre 0-100: ");
        scanf("%f",&porcentaje);
        notaL= porcentaje_a_letra(porcentaje);
        printf("%.2f = %c",porcentaje,notaL);
        break;
    default:
        printf("NO a elegido una opcion valida");
        break;
    }
    return 0;
}