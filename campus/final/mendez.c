
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <stdbool.h>
#include <string.h>


char* extraer_subcadena(const char* cadena, size_t posicion_inicial, size_t posicion_final)
{
    size_t largo = strlen(cadena);
    bool exito = true;
    char* subcadena = NULL;
    if (cadena == NULL || cadena[0] == '\0')
    {
        exito = false;
    }
    if (posicion_inicial > largo ||posicion_final > largo)
    {
        exito = false;
    }
    if (exito == true)
    {
        subcadena = malloc(sizeof(char)*(posicion_final - posicion_inicial));
        if (subcadena == NULL) {
            exito = false;
        }
    }
    if (exito == true)
    {
        size_t largo_subcadena = posicion_final - posicion_inicial;
        for (size_t i = 0; i < largo_subcadena; i++)
        {
            subcadena[i] = cadena[posicion_inicial + i + 1]; //esta como 'texto' en papel
        }
    }
    return subcadena;
}

char* modificar_cadena(char* texto, char* buscar, char* reemplazar) {
    bool subcadena_encontrada = false;
    char* nueva_cadena = NULL;
    bool exito = true;
    if (texto == NULL || buscar == NULL || reemplazar == NULL) {
        exito = false;
    }
    if (exito == true) {
        size_t largo_texto = strlen(texto);
        size_t largo_reemplazar = strlen(reemplazar);

        size_t largo_buscar = strlen(buscar); // no presente en la entrega

        size_t contador = 0;
        size_t posicion_inicial = 0;
        size_t posicion_final = 0;
        bool es_posicion_inicial = true;
        for (size_t i = 0; i < largo_texto; i++) {
            if (texto[i] == buscar[contador]) {
                contador++;
                if (es_posicion_inicial == true) {
                    posicion_inicial = i;
                    es_posicion_inicial = false;
                }
            }
        }
        if (largo_buscar == contador) {
            subcadena_encontrada = true;
            size_t largo_nueva_cadena = largo_texto + largo_reemplazar;
            nueva_cadena = malloc(sizeof(char)* largo_nueva_cadena + 1);
            char* primera_parte = NULL;
            char* segunda_parte = NULL;
            if (nueva_cadena == NULL) {
                exito = false;
            } else {
                if (posicion_final == 0)
                {
                    size_t avanzar = 0;
                    segunda_parte = extraer_subcadena(texto, posicion_final, largo_texto);
                    for(size_t i = 0; i < largo_nueva_cadena; i++){
                        if (i <= posicion_final){
                            nueva_cadena[i] = reemplazar[i];
                        } else {
                            nueva_cadena[i] = segunda_parte[avanzar];
                            avanzar++;
                        }
                    }
                } else {
                    primera_parte = extraer_subcadena(texto,0,posicion_inicial);
                    segunda_parte = extraer_subcadena(texto, posicion_final, largo_nueva_cadena); // largo_segunda_cadena es lo que interpreto que vá acá
                    for (size_t i = 0; i < largo_nueva_cadena; i++){
                        if(i<=posicion_inicial){
                            nueva_cadena[i]=primera_parte[i];
                        } else if (i> posicion_inicial && i <= posicion_final) {
                            nueva_cadena[i] = reemplazar[i - strlen(primera_parte)];
                        
                        } else {
                            nueva_cadena[i] = segunda_parte[i - strlen(primera_parte)- strlen(segunda_parte)];
                        }
                    }
                }
                

            }
        }
    }
    return nueva_cadena;
}