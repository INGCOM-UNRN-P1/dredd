#!/usr/bin/bash

echo "Procesando $1-submissions/$2"
repo="$1-submissions/$2"

if [ -d "$repo" ]; then
    echo "git pull en el repositorio $repo"
    git -C $repo restore "*"
    git -C $repo pull

git_pull_output=$(git -C $repo pull 2>&1)

if [[ $git_pull_output == *"Already up to date."* || $git_pull_output == *"Ya está actualizado."* ]]; then
    echo "El repositorio ya estaba actualizado."
else
    echo "No se puede continuar, ha ocurrido un error en git."
    echo "Git dice\n: $git_pull_output"
    exit 2
fi

    echo "Creacion del informe"
    cat informe/header.md > mensaje.md

    git -C $repo reset --hard HEAD

    printf "\n## Repositorio" >> mensaje.md
    printf "\n**branch/revision:** %s %s\n", "$(git -C $repo rev-parse --abbrev-ref HEAD)", "$(git -C $repo rev-parse --short HEAD)" >> mensaje.md   
    printf "\nInforme creado el `date`\n" >> mensaje.md

    printf "\n## Contenido" >> mensaje.md    
    printf "\n\`\`\`" >> mensaje.md
    ls -hl $repo >> mensaje.md
    printf "\n\`\`\`" >> mensaje.md

    printf "\n## Analisis" >> mensaje.md

    ejercicios=$(find $repo -type d -name "ejercicio*")

    for ejercicio in $ejercicios; do
        echo "Procesando $ejercicio"
        
        printf "\n### sobre \`${ejercicio}\n" >> mensaje.md

        printf "\n#### \`make clean\`\n" >> mensaje.md
        printf "\n\`\`\`\n" >> mensaje.md
        make -C "$ejercicio" clean >> mensaje.md 2>&1
        printf "\n\`\`\`\n" >> mensaje.md

        printf "\n#### \`make test\`\n" >> mensaje.md
        printf "\n\`\`\`\n" >> mensaje.md
        make -C "$ejercicio" test >> mensaje.md 2>&1
        printf "\n\`\`\`\n" >> mensaje.md
        
        printf "\n#### \`make check\`\n" >> mensaje.md
        cat check >> "$ejercicio"/Makefile
        printf "\n\`\`\`\n" >> mensaje.md
        make -C "$ejercicio" check >> mensaje.md 2>&1
        printf "\n\`\`\`\n" >> mensaje.md
        

    done

    git -C $repo reset --hard HEAD

    cat informe/footer.md >> mensaje.md

    echo "Informe listo en $2.md"
    mv mensaje.md $2.md

    printf "\nbranch: %s \trevision: %s\n", "$(git -C $repo rev-parse --abbrev-ref HEAD)", "$(git -C $repo rev-parse --short HEAD)"

    git -C $repo log -n 5 --oneline origin/main

    echo "para completar el siguiente paso:"
    echo "./comment.sh $2"

else
    echo "Clonando el repositorio si no lo estaba para $repo, ejecutar una segunda vez para verificar"
    echo "INGCOM-UNRN-P1/$2.git"
    git clone https://github.com/INGCOM-UNRN-P1/$2.git $repo



fi
