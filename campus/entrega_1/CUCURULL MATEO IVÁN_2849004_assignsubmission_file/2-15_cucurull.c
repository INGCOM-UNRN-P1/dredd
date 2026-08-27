/*
Ejercicio 2.15 - Conversor de Calificaciones
"En este codigo se va a usar un sistema comparmentalizado para
convertir una calificacion a otro y mostrar el resultado por pantalla"

----------------
Nombre y Apellido: Mateo Cucurull
Usuario de GitHub: MattCucurull
*/

#include <stdio.h>
#include <ctype.h>

int numerica_a_alfabetica(){
    float calificacion_numerica = 0;

    printf("Ingrese el valor numerico que quiere convertir a calificacion alfabetica\n");
    printf("Recuerde ingresar valores del 0 al 10\n");
    scanf("%f", &calificacion_numerica);

    while (calificacion_numerica > 10 || calificacion_numerica < 0){
        printf("Su valor %.2f, no es valido, ingrese otro en el rango del 0 al 10 inclusive\n", calificacion_numerica);
        scanf("%f", &calificacion_numerica);
    }

    if (calificacion_numerica < 6){
        printf("Tu calificacion '%.2f' es una F en el sistema alfabetico\n", calificacion_numerica);
    }
    else if (calificacion_numerica >= 6 && calificacion_numerica < 7){
        printf("Tu calificacion '%.2f' es una D en el sistema alfabetico\n", calificacion_numerica);
    }
    else if (calificacion_numerica >= 7 && calificacion_numerica < 8){
        printf("Tu calificacion '%.2f' es una C en el sistema alfabetico\n", calificacion_numerica);
    }
    else if (calificacion_numerica >= 8 && calificacion_numerica < 9){
        printf("Tu calificacion '%.2f' es una B en el sistema alfabetico\n", calificacion_numerica);
    }
    else if (calificacion_numerica >= 9 && calificacion_numerica <= 10){
        printf("Tu calificacion '%.2f' es una A en el sistema alfabetico\n", calificacion_numerica);
    }

    return 0;
}

int numerica_a_porcentual(){
    float calificacion_numerica = 0; 

    printf("Ingrese el valor numerico que quiere convertir a calificacion porcentual\n");
    printf("Recuerde ingresar valores naturales del 0 al 10\n");
    scanf("%f", &calificacion_numerica);
    while (calificacion_numerica > 10 || calificacion_numerica < 0){
        printf("Su valor %.2f, no es valido, ingrese otro en el rango del 0 al 10 inclusive\n", calificacion_numerica);
        scanf("%f", &calificacion_numerica);
    }
    float operacion = (calificacion_numerica * 10);
    printf("Tu calificacion numerica en el sistema porcentual seria del %.0f%%", operacion);
    return 0;
}

int alfabetica_a_numerica(){
    char calificacion_alfabetica = '0';

    printf("Ingrese la calificacion alfabetica que quiere convertir a numerica\n");
    printf("Recuerde que solo estan contempladas las letras A, B, C, D y F\n");
    scanf(" %c", &calificacion_alfabetica);
    calificacion_alfabetica = toupper(calificacion_alfabetica);
    switch (calificacion_alfabetica)
    {
    case 'F':
        printf("Tu 'F' puede ser cualquier valor del 0 a menos que el 6 \n");
        break;
    case 'D':
        printf("Tu 'D' puede ser cualquier nota del 6 a menos que el 7 \n");
        break;
    case 'C':
        printf("Tu 'C' puede ser cualquier calificacion del 7 a menos que el 8 \n");
        break;
    case 'B':
        printf("Tu 'B' puede ser cualquier calificacion del 8 a menos que el 9 \n");
        break;
    case 'A':
        printf("Tu 'A' puede ser cualquier valor del 9 al 10 en el sistema numerico \n");
        break;
    default:
        printf("Tu nota no era valida dentro del sistema alfabetico \n");
        break;
    }

    return 0;
}

int alfabetica_a_porcentual(){
    char calificacion_alfabetica = '0';

    printf("Ingrese la calificacion alfabetica que quiere convertir a numerica\n");
    printf("Recuerde que solo estan contempladas las letras A, B, C, D y F\n");
    scanf(" %c", &calificacion_alfabetica);
    calificacion_alfabetica = toupper(calificacion_alfabetica);
    switch (calificacion_alfabetica)
    {
    case 'F':
        printf("Tu 'F' puede ser cualquier valor del 0%% a menos que el 60%% \n");
        break;
    case 'D':
        printf("Tu 'D' puede ser cualquier nota del 60%% a menos que el 70%% \n");
        break;
    case 'C':
        printf("Tu 'C' puede ser cualquier calificacion del 70%% a menos que el 80%% \n");
        break;
    case 'B':
        printf("Tu 'B' puede ser cualquier calificacion del 80%% a menos que el 90%% \n");
        break;
    case 'A':
        printf("Tu 'A' puede ser cualquier valor del 90%% al 100%% en el sistema porcentual \n");
        break;
    default:
        printf("Tu nota no era valida dentro del sistema alfabetico \n");
        break;
    }

    return 0;
}

int porcentual_a_numerica(){
    int calificacion_numerica = 0;

    printf("Ingrese la calificacion porcentual que quiere convertir a numerica\n");
    printf("Recuerde que estan contemplados los naturales del 0 al 100 \n");
    scanf("%d", &calificacion_numerica);

    while (calificacion_numerica > 100 || calificacion_numerica < 0){
        printf("Su valor %d, no es valido, ingrese otro en el rango del 0 al 10 inclusive que sea natural\n", calificacion_numerica);
        scanf("%d", &calificacion_numerica);        
    }
    float operacion = (calificacion_numerica / 10.00);
    printf("Tu calificacion %d%% en el sistema numerico seria el numero: '%.2f' \n", calificacion_numerica, operacion);

    return 0;
}

int porcentual_a_alfabetica(){
    int calificacion_numerica = 0;

    printf("Ingrese la calificacion porcentual que quiere convertir a alfabetica \n");
    printf("Recuerde que estan contemplados los naturales del 0%% al 100%% \n");
    scanf("%d", &calificacion_numerica);

    while (calificacion_numerica > 100 || calificacion_numerica < 0){
        printf("Su valor %d, no es valido, ingrese otro en el rango del 0%% al 100%% inclusive entre los naturales\n", calificacion_numerica);
        scanf("%d", &calificacion_numerica);        
    }    

    if (calificacion_numerica < 60){
        printf("Tu calificacion %d%% es una 'F' en el sistema alfabetico \n", calificacion_numerica);
    }
    else if (calificacion_numerica >= 60 && calificacion_numerica < 70){
        printf("Tu calificacion %d%% es una 'D' en el sistema alfabetico \n", calificacion_numerica);
    }
    else if (calificacion_numerica >= 70 && calificacion_numerica < 80){
        printf("Tu calificacion %d%% es una 'C' en el sistema alfabetico \n", calificacion_numerica);
    }
    else if (calificacion_numerica >= 80 && calificacion_numerica < 90){
        printf("Tu calificacion %d%% es una 'B' en el sistema alfabetico \n", calificacion_numerica);
    }
    else if (calificacion_numerica >= 90 && calificacion_numerica <= 100){
        printf("Tu calificacion %d%% es una 'A' en el sistema alfabetico \n", calificacion_numerica);
    }
    return 0;
}

int main(){
    int eleccion_del_usuario = 0;

    printf("Eliga una opcion de conversion con los numeros asociados para su calificacion: \n");
    printf("1. Numerica a alfabetica\n");
    printf("2. Numerica a porcentual\n");
    printf("3. Alfabetica a numerica\n");
    printf("4. Alfabetica a porcentual\n");
    printf("5. Porcentual a numerica\n");
    printf("6. Porcentual a alfabetica\n");
    scanf("%d", &eleccion_del_usuario);

    switch(eleccion_del_usuario){
        case 1:
            numerica_a_alfabetica();
            break;
        case 2:
            numerica_a_porcentual();
            break;
        case 3:
            alfabetica_a_numerica();
            break;
        case 4:
            alfabetica_a_porcentual();
            break;
        case 5:
            porcentual_a_numerica();
            break;
        case 6:
            porcentual_a_alfabetica();
            break;
        default:
            printf("No pudimos interpretar su eleccion correctamente\n");
            break;
    }

    return 0;
}