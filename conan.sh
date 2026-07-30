#!/usr/bin/env bash
# Script para evaluar proyectos estructurados en ejercicios con Makefiles

set -euo pipefail

if [ "$#" -ne 2 ]; then
    echo "Uso: $0 <nombre-ejercicio> <nombre-estudiante>"
    exit 1
fi

ejercicio_name="$1"
estudiante_name="$2"
repo="${ejercicio_name}-submissions/${estudiante_name}"

if [ -d "$repo" ]; then
    echo "Actualizando repositorio en $repo..."
    git -C "$repo" restore "*" || true
    
    if ! git -C "$repo" pull; then
        echo "No se puede continuar, ha ocurrido un error en git pull."
        exit 2
    fi

    echo "Creando el informe..."
    git -C "$repo" reset --hard HEAD

    mkdir -p "informe"
    if [ -f "informe/header.md" ]; then
        cat "informe/header.md" > mensaje.md
    else
        echo "# Informe de Corrección" > mensaje.md
    fi

    printf "\n## Repositorio\n" >> mensaje.md
    printf "**branch/revision:** %s %s\n" "$(git -C "$repo" rev-parse --abbrev-ref HEAD)" "$(git -C "$repo" rev-parse --short HEAD)" >> mensaje.md   
    printf "\nInforme creado el %s\n" "$(date)" >> mensaje.md

    printf "\n## Contenido\n" >> mensaje.md    
    printf "\n\`\`\`\n" >> mensaje.md
    ls -hl "$repo" >> mensaje.md
    printf "\n\`\`\`\n" >> mensaje.md

    printf "\n## Análisis\n" >> mensaje.md

    # Buscar directorios de ejercicios
    ejercicios=$(find "$repo" -type d -name "ejercicio*" | sort)

    for ejercicio in $ejercicios; do
        echo "Procesando $ejercicio..."

        printf "\n### Sobre \`%s\`\n" "$(basename "$ejercicio")" >> mensaje.md

        printf "\n#### \`make clean\`\n" >> mensaje.md
        printf "\n\`\`\`text\n" >> mensaje.md
        timeout --foreground 1m make -C "$ejercicio" clean >> mensaje.md 2>&1 || true
        printf "\n\`\`\`\n" >> mensaje.md

        printf "\n#### \`make test\`\n" >> mensaje.md
        printf "\n\`\`\`text\n" >> mensaje.md
        timeout --foreground 1m make -C "$ejercicio" test >> mensaje.md 2>&1 || true
        printf "\n\`\`\`\n" >> mensaje.md

        printf "\n#### \`make check\`\n" >> mensaje.md
        if [ -f "check" ]; then
            cat check >> "$ejercicio/Makefile"
        fi
        printf "\n\`\`\`text\n" >> mensaje.md
        timeout --foreground 1m make -C "$ejercicio" check >> mensaje.md 2>&1 || true
        printf "\n\`\`\`\n" >> mensaje.md
    done

    # Limpiar modificaciones al Makefile del estudiante
    git -C "$repo" reset --hard HEAD

    if [ -f "informe/footer.md" ]; then
        cat "informe/footer.md" >> mensaje.md
    fi

    echo "Informe generado con éxito."
    mv mensaje.md "${estudiante_name}.md"

    printf "\nbranch: %s \trevision: %s\n" "$(git -C "$repo" rev-parse --abbrev-ref HEAD)" "$(git -C "$repo" rev-parse --short HEAD)"
    git -C "$repo" log -n 5 --oneline origin/main || true

    echo ""
    echo "Para completar el siguiente paso ejecute:"
    echo "./comment.sh ${estudiante_name}"

else
    echo "Clonando el repositorio porque no existía..."
    git clone "https://github.com/INGCOM-UNRN-P1/${estudiante_name}.git" "$repo"
    echo "Ejecute el script nuevamente para analizar."
fi
