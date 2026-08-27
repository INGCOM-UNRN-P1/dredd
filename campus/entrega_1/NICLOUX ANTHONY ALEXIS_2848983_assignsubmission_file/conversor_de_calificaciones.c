/*
Ejercicio 1.7 - Conversor de Calificaciones
Convertí entre diferentes sistemas de calificación: numérica (0-10), letra (A-F), porcentaje (0-100).

--------------------

Anthony Alexis Nicloux
alex44523
*/

#include <stdio.h>
#include <stdbool.h>

int main(){
    char calificacion_letra = '0';
    float calificacion_numerica = 0.0;
    int calificacion_porcentaje = 0;
    // Para navegar por el switch
    char navegar = '0';
    while (true){
        printf ("Para convertir la calificacion numerica (0-10) --> calificacion A-F y calificacion porcentaje (0-100) escriba \"1\"\n");
        printf ("Para convertir la calificacion porcentaje (0-100) --> calificacion A-F y calificacion numerica (0-10) escriba \"2\"\n");
        printf ("Para convertir la calificacion A-F --> calificacion numerica (0-10) y calificacion porcentaje (0-100) escriba \"3\"\n");
        printf ("Para salir escriba \"0\"\n");
        scanf (" %c", &navegar);
        switch (navegar){
            case '1':
                printf ("Ingrese la calificacion numerica (0-10): ");
                scanf ("%f", &calificacion_numerica);
                if (calificacion_numerica >= 9.0){
                    calificacion_letra = 'A';
                }else if (calificacion_numerica >= 8.0){
                    calificacion_letra = 'B';
                }else if (calificacion_numerica >= 7.0){
                    calificacion_letra = 'C';
                }else if (calificacion_numerica >= 6.0){
                    calificacion_letra = 'D';
                }else {
                    calificacion_letra = 'F';
                }
                // El '(int)' convierte el float a int
                calificacion_porcentaje = (int)(calificacion_numerica * 10);
                printf ("La calificacion A-F es: %c\n", calificacion_letra);
                printf ("La calificacion porcentaje es: %d\n", calificacion_porcentaje);
                break;
            case '2':
                printf ("Ingrese la calificacion porcentaje (0-100): ");
                scanf ("%d", &calificacion_porcentaje);
                // El '(float)' convierte el int a float
                calificacion_numerica = (float)calificacion_porcentaje / 10.0;
                if (calificacion_porcentaje >= 90){
                    calificacion_letra = 'A';
                }else if (calificacion_porcentaje >= 80){
                    calificacion_letra = 'B';
                }else if (calificacion_porcentaje >= 70){
                    calificacion_letra = 'C';
                }else if (calificacion_porcentaje >= 60){
                    calificacion_letra = 'D';
                }else {
                    calificacion_letra = 'F';
                }
                printf ("La calificacion A-F es: %c\n", calificacion_letra);
                printf ("La calificacion numerica es: %.1f\n", calificacion_numerica);
                break;
            case '3':
                printf ("Ingrese la calificacion A-F: ");
                scanf (" %c", &calificacion_letra);
                switch (calificacion_letra){
                    case 'A':
                        calificacion_numerica = 10.0;
                        calificacion_porcentaje = 100;
                        break;
                    case 'B':
                        calificacion_numerica = 8.5;
                        calificacion_porcentaje = 85;
                        break;
                    case 'C':
                        calificacion_numerica = 7.5;
                        calificacion_porcentaje = 75;
                        break;
                    case 'D':
                        calificacion_numerica = 6.5;
                        calificacion_porcentaje = 65;
                        break;
                    case 'F':
                        calificacion_numerica = 5.0;
                        calificacion_porcentaje = 50;
                        break;
                }
                printf ("La calificacion numerica es: %.1f\n", calificacion_numerica);
                printf ("La calificacion porcentaje es: %d\n", calificacion_porcentaje);
                break;
            case '0':
                printf ("Adios\n");
                return 0;
        }
    }
}