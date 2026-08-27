/*
Ejercicio 7 - Conversor de Calificaciones
Convertí entre diferentes sistemas de 
calificación: numérica (0-10), letra (A-F), porcentaje (0-100).
-----------------
Morena Suso
MorenaSuso
*/
#include <stdio.h>


char porcentajeALetra(int nota)
{
    if (nota >= 90)
        return 'A';
    else if (nota >= 80)
        return 'B';
    else if (nota >= 70)
        return 'C';
    else if (nota >= 60)
        return 'D';
    else
        return 'F';
}

int porcentajeANumero(int nota)
{
    return nota / 10;
}

int numeroAPorcentaje (int nota)
{
    return nota * 10;
}

char numeroALetra (int nota)
{
    if (nota >= 9)
        return 'A';
    else if (nota >= 8)
        return 'B';
    else if (nota >= 7)
        return 'C';
    else if (nota >= 6)
        return 'D';
    else
        return 'F';
}
 
int letraANumero (char notaLetra)
{
    if (notaLetra == 'A')
        return 10;
    else if (notaLetra == 'B')
        return 8;
    else if (notaLetra == 'C')
        return 7;
    else if (notaLetra == 'D')
        return 6;
    else
        return 5;
}

int letraAPorcentaje (char notaLetra)
{
    
    if (notaLetra == 'A')
        return 100;
    else if (notaLetra == 'B')
        return 80;
    else if (notaLetra == 'C')
        return 70;
    else if (notaLetra == 'D')
        return 60;
    else if (notaLetra == 'F')
        return 50;

}
int main()
{

int opcion = 0;
printf("Seleccione una opcion: \n" "1. Porcentaje a letra\n" 
    "2. Porcentaje a nuemro\n"  "3. Numero a letra\n"  
    "4. Numero a porcentaje\n"  "5. Letra a porcentaje\n"  "6. Letra a numero\n");
scanf("%d", &opcion);
 
if(opcion >= 1 && opcion <= 4)
{
    int nota;
    char notaLResultado;
    printf("Ingrese su nota: \n");
    scanf("%d", &nota);
    
    switch (opcion)
         {
             case 1:
             notaLResultado = porcentajeALetra(nota);
             printf("%c\n", notaLResultado);
             break;
             case 2:
             nota = porcentajeANumero(nota);
             printf("%d\n", nota);
             break;
             case 3:
             notaLResultado = numeroALetra(nota);
             printf("%c\n", notaLResultado);
             break;
             case 4:
             nota = numeroAPorcentaje(nota);
             printf("%d\n", nota);
             break;
         }
             
}
else
{
    char notaLetra;
    int notaNResultado;
    printf("Ingrese su nota: \n");
    scanf(" %c", &notaLetra);
     switch (opcion)
         {
             case 5:
             notaNResultado = letraAPorcentaje(notaLetra);
             printf("%d\n", notaNResultado);
             break;
             case 6:
             notaNResultado = letraANumero(notaLetra);
             printf("%d\n", notaNResultado);
             break;
         }
}
return 0;
}