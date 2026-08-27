/*
Ejercicio 7 – Conversor de Calificaciones 
Convertí entre diferentes sistemas de calificación: numérica (0-10), letra (A-F), porcentaje (0-100).
-----------------
Facundo Argerich
Github: ArgerichFacu
*/

#include <stdio.h>

char numero_a_letra (float numero_usuario)
{
    char letra = '\0';
    //De Decimal a Letra
    if (numero_usuario >= 9 && numero_usuario <= 10)
    {
        letra = 'A';
    }
    else if (numero_usuario >= 8 && numero_usuario < 9)
    {
         letra = 'a';
    }
    else if (numero_usuario >= 7 && numero_usuario < 8)
    {
         letra = 'B';
    }
    else if (numero_usuario >= 6 && numero_usuario < 7)
    {
         letra = 'b';
    }
    else if (numero_usuario >= 5 && numero_usuario < 6)
    {
         letra = 'C';
    }
    else if (numero_usuario >= 4 && numero_usuario < 5)
    {
         letra = 'c';
    }
    else if (numero_usuario >= 3 && numero_usuario < 4)
    {
         letra = 'D';
    }
    else if (numero_usuario >= 2 && numero_usuario < 3)
    {
         letra = 'd';
    }
    else if (numero_usuario >= 1 && numero_usuario < 2)
    {
         letra = 'F';
    }
    else if (numero_usuario >= 0 && numero_usuario < 1)
    {
         letra = 'f';
    }

    return letra;
}

float numero_a_porcentaje (float numero_usuario)
{
    float porcentaje = 0.0;

    porcentaje = numero_usuario * 10;

    return porcentaje;
}

float letra_a_numero (char letra_usuario)
{
    float numero = 0.0;

    //De Letra a Decimal
    if (letra_usuario == 'A')
    {
        numero = 10.0;
    }
    else if (letra_usuario == 'a')
    {
        numero = 9.0;
    }
    else if (letra_usuario == 'B')
    {
        numero = 8.0;
    }
    else if (letra_usuario == 'b')
    {
        numero = 7.0;
    }
    else if (letra_usuario == 'C')
    {
        numero = 6.0;
    }
    else if (letra_usuario == 'c')
    {
        numero = 5.0;
    }
    else if (letra_usuario == 'D')
    {
        numero = 4.0;
    }
    else if (letra_usuario == 'd')
    {
        numero = 3.0;
    }
    else if (letra_usuario == 'F')
    {
        numero = 2.0;
    }
    else if (letra_usuario == 'f')
    {
        numero = 1.0;
    }

    return numero;
}

float letra_a_porcentaje (char letra_usuario)
{
    float porcentaje = 0.0;
    float numero = 0.0;
    
    numero = letra_a_numero(letra_usuario);
    porcentaje = numero_a_porcentaje(numero);

    return porcentaje;
}

float porcentaje_a_numero (float porcentaje_usuario)
{
    float numero = 0;

    numero = porcentaje_usuario / 10;

    return numero;
}

char porcentaje_a_letra (float porcentaje_usuario)
{
    char letra = '\0';
    float numero = 0.0;
    
    numero = porcentaje_a_numero(porcentaje_usuario);
    letra = numero_a_letra(numero);

    return letra;
}

int main ()
{
    char letra_usuario = '\0';
    float numero_usuario = 0.0;
    float porcentaje_usuario = 0.0;
    char letra = '\0';
    float numero = 0.0;
    float porcentaje = 0.0;
    
    int option;

    do
    {
        printf("Seleccione una opcion:\n");
        printf("1. De Numero a Letra.\n");
        printf("2. De Numero a Porcentaje.\n");
        printf("3. De Letra a numero.\n");
        printf("4. De Letra a Porcentaje.\n");
        printf("5. De Porcentaje a numero.\n");
        printf("6. De Porcetanje a Letra.\n");
        printf("7. Salio.\n");
        printf("Opcion: ");
        scanf("%d", &option);

        switch (option)
        {
        case 1:
            printf("Ingrese su calificacion numerica (0-10): ");
            scanf("%f", &numero_usuario);

            letra = numero_a_letra(numero_usuario);

            printf("Su calificacion de tipo letra (Aa-Ff) es: %c\n\n", letra);

            break;
        
        case 2:
            printf("Ingrese su calificacion numerica (0-10): ");
            scanf("%f", &numero_usuario);

            porcentaje = numero_a_porcentaje(numero_usuario);

            printf("Su calificacion porcentual (1-100) es: %.2f%%\n\n", porcentaje);

            break;

        case 3:
            printf("Ingrese su calificacion de tipo letra (Aa-Ff): ");
            scanf(" %c", &letra_usuario);

            numero = letra_a_numero(letra_usuario);

            printf("Su calificacion numerica (1-10) es: %.2f\n\n", numero);

            break;    

        case 4:
            printf("Ingrese su calificacion de tipo letra (Aa-Ff): ");
            scanf(" %c", &letra_usuario);

            porcentaje = letra_a_porcentaje(letra_usuario);

            printf("Su calificacion porcentual (1-100) es: %.2f%%\n\n", porcentaje);

            break;

        case 5:
            printf("Ingrese su calificacion porcentual (1-100): ");
            scanf("%f", &porcentaje_usuario);

            numero = porcentaje_a_numero(porcentaje_usuario);

            printf("Su calificacion numerica (1-10) es: %.2f\n\n", numero);

            break;

        case 6:
            printf("Ingrese su calificacion porcentual (1-100): ");
            scanf("%f", &porcentaje_usuario);

            letra = porcentaje_a_letra(porcentaje_usuario);

            printf("Su calificacion de tipo letra (Aa-Ff) es: %c\n\n", letra);

            break;

        case 7:
            printf("\n Saliendo del programa... \n");

            break;

        default:
            printf("Ingrese una opcion valida.\n\n");
            break;
        }
    } while (option != 7);

    return 0;
}