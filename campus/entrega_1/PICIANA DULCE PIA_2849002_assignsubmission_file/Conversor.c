/*
Ejercicio 7 – Conversor de calificaciones
Convertir entre diferentes sistemas de calificación:
numérica(0-10),letra (A-F),porcentaje(0-100)
Dulce Piciana
dulcepiciana
*/
#include<stdio.h>
int main()
{
    int opcion = 0;
    char letra = '\0';
    float numero= 0.0 ;
    int porcentaje= 0;


    printf("=== Menú de conversiones ===\n");
    printf("1. Numérica a Letra\n");
    printf("2. Letra a Numérica\n");
    printf("3. Numérica a Porcentaje\n");
    printf("4. Porcentaje a Numérica\n");
    printf("5. Letra a Porcentaje\n");
    printf("6. Porcentaje a Letra\n");
    printf("Elegí una opcion(1-6): ");
    scanf("%d", &opcion);
    switch(opcion)
    {
    case 1:
        printf("Ingrese nota numérica (0-10):");
        scanf("%f",&numero);
        if(numero>=0.0 && numero <= 10.0 )
        {
            if  (numero>= 9.0)
            {
                printf("letra = A\n ");
            }
            else if (numero >= 8.0)
            {
                printf("letra = B\n ");
            }
            else if (numero >= 7.0)
            {
                printf("letra = C\n ");
            }
            else if (numero >= 6.0)
            {
                printf("letra = D\n ");
            }
            else 
            {
                printf("letra = F\n ");
            }
        }
        else
        {
        printf("Error:La nota debe estar entre 0 y 10");
        }
    break;

        
    case 2:
        printf("Ingrese letra (A-F):");
        scanf("%c",&letra);
        switch (letra)
        {
        case 'A':
            numero = 9.5;
            printf("La nota numérica es:",numero);
            break;
        case 'B':
            numero = 8.5;
            printf("La nota numérica es:",numero);
            break;
        case 'C':
            numero =  7.5;
            printf("La nota numérica es:",numero);
            break;
        case 'D':
            numero = 6.5;
            printf("La nota numérica es:", numero);
        case 'F':
            numero = 5.0;
            printf("La nota numérica es:",numero);
        default:
            printf("Error: Letra no válida(Usar A,B,C,D o F");
            break;
        }
        break;
    case 3:
    printf("Ingrese nota numérica (0-10:)" );
    scanf("%f",&numero);
    if (numero >= 0.0 && numero <= 10.00)
    {
        porcentaje = numero * 10;
        printf("La calificacion es:", porcentaje);
    }
    else 
    {
        printf("Error: La nota debe estar entre 0 y 10");
    }
    case 4:
    printf("Ingrese porcentaje (0-100):");
    scanf("%d", &porcentaje);
    if (porcentaje >= 0 && porcentaje <= 100)
    {
        numero = porcentaje / 10.0;
        printf("La nota numérica es:",numero);
    }
    else
    {
        printf("Error: Porcentaje debe estar entre 0 y 100");
    }
    case 5:
    printf("Ingrese letra (A-F):");
    scanf("%c", letra);
    switch (letra)
    {
    case 'A':
        porcentaje = 95;
        printf("La calificación es: ", porcentaje);
    case 'B':
        porcentaje = 85;
        printf("La calificación es:", porcentaje);
    case 'C':
        porcentaje = 75;
        printf("La calificación es:", porcentaje);
    case 'D':
        porcentaje = 65;
        printf("La calificación es:", porcentaje);
    case 'F':
        porcentaje = 50;
        printf("La calificación es:",porcentaje);
        break;
    
    default:
        printf("Error: Letra no válida");
        break;
    }
    case 6:
    printf("Ingrese porcentaje (0-100):");
    scanf("%d",&porcentaje);
    if (porcentaje >= 0 && porcentaje <= 100)
    {
        if (porcentaje >= 90)
        {
            printf("Letra = A\n");
        }
        else if (porcentaje >= 80)
        {
            printf("Letra = B\n ");
        }
        else if (porcentaje >=70)
        {
            printf("Letra = C\n ");
        }
        else if (porcentaje >= 60)
        {
            printf("Letra = D\n ");
        }
        else 
        {
            printf("Letra = F\n ");
        }
        printf("La letra es:",letra);
        
    }
    else 
    {
        printf("El porcentaje debe estar entre 0 y 100");
    }
    default:
    printf("Opción no válida (debe ser de 1 a 6)");
    }
    return 0;
}