/*
Ejercicio 1.7 - Conversor de Calificaciones ⭐⭐⭐⭐☆
Convertí entre diferentes sistemas de calificación: numérica (0-10), letra (A-F), porcentaje (0-100).
-----------------
Nombre y Apellido: Lautaro Costantini
Usuario Github: L-Ezql
*/

#include <stdio.h>
#include <ctype.h>

int conversor_af_10 (int mod)
{
    char calificacion = ' ';
    printf("Ingresar calificacion A-F: ");
    scanf(" %c", &calificacion);
    if(isalpha(calificacion))
    {
        printf("%c es ", calificacion);
        switch (tolower(calificacion))
        {
        case 'a':
            printf("%d-%d\n", 10*mod, 9*mod);
            break;
        case 'b':
            printf("%d-%d\n", 8*mod, 7*mod);
            break;
        case 'c':
            printf("%d-%d\n", 6*mod, 5*mod);
            break;
        case 'd':
            printf("%d-%d\n", 4*mod, 3*mod);
            break;
        case 'f':
            printf("%d-%d\n", 2*mod, 1*mod);
            break;
        default:
            printf("INVALIDO\n");
        }
    } 
    else
    {
        printf("%c es INVALIDO\n", calificacion);
        return 0;
    }
}

int conversor_10_af (int mod)
{
    int calificacion = 0;
    printf("Ingresar calificacion 0-%d: ", 10*mod);
    scanf("%d", &calificacion);
    
    printf("%d es ", calificacion);
    switch (calificacion/mod)
    {
    case 10:
    case 9:
        printf("A\n");
        break;
    case 8:
    case 7:
        printf("B\n");
        break;
    case 5:
    case 6:
        printf("C\n");
        break;
    case 3:
    case 4:
        printf("D\n");
        break;
    case 2:
    case 1:
        printf("F\n");
        break;
    default:
        printf("INVALIDO\n");
    }
}

int conversor_10_10 (int rango, float multiplicador)
{
    int calificacion = 0;
    printf("Ingresar calificacion 0-%d: ", rango);
    scanf("%d", &calificacion);
    if (calificacion < 0 || calificacion > rango)
    {
        printf("%d es INVALIDO\n", calificacion);
    }
    else
    {
        printf("%d es %.1f\n", calificacion, calificacion*multiplicador);
    }
    
}

int main()
{
    int opcion = 0;
    int nota = 0;
    printf("CONVERSOR DE CALIFICACION: ingresar opcion\n"
        "1. A-F a 0-10\n"
        "2. A-F a 0-100\n"
        "3. 0-10 a A-F\n"
        "4. 0-10 a 0-100\n"
        "5. 0-100 a A-F\n"
        "6. 0-100 a 0-10\n");
    
    printf("Opcion (1-6): ");
    scanf("%d", &opcion);
    
    switch (opcion)
    {
    case 1:
        conversor_af_10(1);
        break;
    case 2:
        conversor_af_10(10);
        break;
    case 3:
        conversor_10_af(1);
        break;
    case 4:
        conversor_10_10(10, 10);
        break;
    case 5:
        conversor_10_af(10);
        break;
    case 6:
        conversor_10_10(100, 0.1);
        break;
    default:
        printf("OPCION INVALIDA\n");
    }
return 0;
}