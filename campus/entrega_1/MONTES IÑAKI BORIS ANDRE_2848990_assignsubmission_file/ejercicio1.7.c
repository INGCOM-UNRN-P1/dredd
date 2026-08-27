/*
Ejercicio 1.7 – Conversor de calificaciones
Convertí entre diferentes sistemas de calificación: numérica (0-10), letra (A-F), porcentaje (0-100).
-----------------
Iñaki Montes
iniaki12
*/


#include <stdio.h>

char numerica_a_letra(float nota) //funcion 1
{
    if (nota == 10)
    {
        return 'A';
    }
    
    else if (nota >= 9)
    {
    return 'a';
    }
    else if (nota >= 8)
    {
        return 'B';
    }
    else if (nota >= 7)
    {
        return 'C';
    }
    else if (nota >= 6)
    {
        return 'D';
    }
    else
    {
        return 'F';
    }
}

float numerica_a_porcentaje(float nota) //funcion 2
{
    return nota * 10;
}

float porcentaje_a_numerica(float porcentaje) //funcion 3
{
    return porcentaje / 10;
}

char porcentaje_a_letra(float porcentaje) //funcion 4
{
    float nota = porcentaje_a_numerica(porcentaje);
    return numerica_a_letra(nota);
}

float letra_a_numerica(char letra) //funcion 5
{
    if (letra == 'A')
    {
        return 10;
    }
    else if (letra == 'a')
    {
        return 9;
    }
    else if (letra == 'B')
    {
        return 8;
    }
    else if (letra == 'C')
    {
        return 7;
    }
    else if (letra == 'D')
    {
        return 6;
    }
    else if (letra == 'F')
    {
        return 5;
    }
    return 0;
}

float letra_a_porcentaje(char letra) //funcion 6
{
    return letra_a_numerica(letra) * 10;
}

int main()
{
    float notanum = 0;
    float porcentaje = 0.00;
    char letra = '\0';
    int opcion = 0;
    do
    {
        printf("convertidor de notas\n");
        printf("opcion 1: calificacion numerica a porcentaje\n"); 
        printf("opcion 2: calificacion numerica a letra\n");
        printf("opcion 3: calificacion porcentaje a numerica\n");
        printf("opcion 4: calificacion procentaje a letra\n");
        printf("opcion 5: calificacion letra a numerica\n");
        printf("opcion 6: calificacion letra a porcentaje\n");
        printf("opcion 7: salir\n");
        printf("elija una opcion: ");
        scanf("%d", &opcion);
        switch (opcion)
        {

        case 1: //numerica a porcentaje
            printf("ingrese la nota numerica: ");
            scanf("%f", &notanum);
            if (notanum < 0 || notanum > 10)
            {
            printf("Failed, la nota debe ser entre 0 y 10\n");
            }
            else
            {
                printf("el resultado es %.2f %%\n", numerica_a_porcentaje(notanum));
            }
            break;

        case 2: //numerica a letra
            printf("ingrese nota numerica: ");
            scanf("%f", &notanum);
            if(notanum < 0 || notanum > 10)
            {
                printf("Failed, la nota debe ser entre 0 y 10\n");
            }
            else
            {
                printf("el resultado es %c\n", numerica_a_letra(notanum));
            }
            break;

        case 3: //porcentaje a numerica
            printf("ingrese el porcentaje: ");
            scanf("%f", &porcentaje);
            if (porcentaje < 0 || porcentaje > 100)
            {
                printf("Failed, debe estar entre el rango de 0 a 100\n");
            }
            else
            {
                printf("el resultado es %f\n", porcentaje_a_numerica(porcentaje));
            }
            break;

        case 4: //porcentaje a letra
            printf("ingrese el porcentaje: ");
            scanf("%f", &porcentaje);
            if (porcentaje < 0 || porcentaje > 100)
            {
                printf("Failed, debe estar entre el rango de 0 a 100\n");
            }
            else
            {
                printf("el resultado es %c\n", porcentaje_a_letra(porcentaje));
            }
            break;

        case 5: //letra a numerica
            printf("ingrese letra: ");
            scanf(" %c", &letra);
            if (letra == 'A' || letra == 'a' || letra == 'B' || letra == 'C' || letra == 'D' || letra == 'F')
            {
                printf("el resultado es %.2f\n", letra_a_numerica(letra));
            }
            else
            {
                printf("Failed, ingrese una letra que sea valida\n");
            }
            break;

        case 6: //letra a porcentaje
            printf("ingrese letra: ");
            scanf(" %c", &letra);
            if (letra == 'A' || letra == 'a' || letra == 'B' || letra == 'C' || letra == 'D' || letra == 'F')
            {
                printf("el resultado es %.2f %%\n", letra_a_porcentaje(letra));
            }
            else
            {
                printf("Failed, ingrese una letra que sea valida\n");
            }
            break;

        case 7:
            printf("¡Adios!");
            break;

        default:
            printf("opcion invalida, ingrese una opcion del 1 al 7\n");
            break;
        }
    }
    while (opcion != 7);
    return 0;
}