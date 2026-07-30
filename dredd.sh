#!/usr/bin/env bash
# Script para evaluar proyectos C directamente sobre archivos fuentes

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
    
    # Intentar hacer pull de forma segura
    if ! git -C "$repo" pull; then
        echo "No se puede continuar, ha ocurrido un error al actualizar con git pull."
        exit 2
    fi

    echo "Creando el informe..."
    mkdir -p "informe"
    if [ -f "informe/header.md" ]; then
        cat "informe/header.md" > mensaje.md
    else
        echo "# Informe de Corrección" > mensaje.md
    fi

    printf "\n## Repositorio\n" >> mensaje.md
    printf "**branch/revision:** %s %s\n" "$(git -C "$repo" rev-parse --abbrev-ref HEAD)" "$(git -C "$repo" rev-parse --short HEAD)" >> mensaje.md   
    printf "\nInforme creado el %s\n" "$(date)" >> mensaje.md

    printf "\n### Archivos contenidos\n" >> mensaje.md    
    printf "\n\`\`\`\n" >> mensaje.md
    ls -hl "$repo" >> mensaje.md
    printf "\n\`\`\`\n" >> mensaje.md

    printf "\n## Análisis\n" >> mensaje.md

    # Buscar archivos .c omitiendo directorios ocultos (como .git)
    c_files=$(find "$repo" -maxdepth 3 -name "*.c" -not -path '*/.*')

    for c_file in $c_files; do
        echo "Analizando: $c_file"
        printf "\n### Sobre \`%s\`\n" "$(basename "$c_file")" >> mensaje.md
        
        printf "\n#### gcc -Wall -Wextra\n" >> mensaje.md
        printf "\n\`\`\`text\n" >> mensaje.md
        gcc -c -fanalyzer -Wall -Wextra "$c_file" -o /dev/null >> mensaje.md 2>&1 || true
        printf "\n\`\`\`\n" >> mensaje.md

        printf "\n#### cppcheck\n" >> mensaje.md
        printf "\n\`\`\`text\n" >> mensaje.md
        cppcheck --addon=verificador.py --quiet --library=posix --language=c --enable=all "$c_file" >> mensaje.md 2>&1 || true
        printf "\n\`\`\`\n" >> mensaje.md

        printf "\n#### splint\n" >> mensaje.md
        printf "\n\`\`\`text\n" >> mensaje.md
        if command -v splint &> /dev/null; then
            splint -hints +showscan +showalluses +stats -exportlocal "$c_file" >> mensaje.md 2>&1 || true
        else
            echo "splint no está instalado" >> mensaje.md
        fi
        printf "\n\`\`\`\n" >> mensaje.md

        printf "\n#### clang-tidy\n" >> mensaje.md
        printf "\n\`\`\`text\n" >> mensaje.md
        if command -v clang-tidy &> /dev/null; then
            clang-tidy -header-filter=.* --config-file=tidy "$c_file" -- >> mensaje.md 2>&1 || true
        else
            echo "clang-tidy no está instalado" >> mensaje.md
        fi
        printf "\n\`\`\`\n" >> mensaje.md
    done

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
