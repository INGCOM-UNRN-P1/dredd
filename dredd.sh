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


    printf "\n## Repositorio" >> mensaje.md
    printf "\n**branch/revision:** %s %s\n", "$(git -C $repo rev-parse --abbrev-ref HEAD)", "$(git -C $repo rev-parse --short HEAD)" >> mensaje.md   
    printf "\nInforme creado el `date`\n" >> mensaje.md

    printf "\n### Archivos contenidos" >> mensaje.md    
    printf "\n\`\`\`" >> mensaje.md
    ls -hl $repo >> mensaje.md
    printf "\n\`\`\`" >> mensaje.md

    printf "\n## Analisis" >> mensaje.md

    c_files=$(find $repo -name "*.c")

    for c_file in $c_files; do
        echo ""
        printf "\n### sobre \`${c_file}\n" >> mensaje.md
        printf "\n#### gcc -Wall -Wextra\n" >> mensaje.md
        printf "\n\`\`\`\n" >> mensaje.md
        gcc -c -fanalyzer -Wall -Wextra $c_file -o a >> mensaje.md 2>&1
        exit_status=$?
        printf "\n\`\`\`\n" >> mensaje.md
        if [ $exit_status -eq 0 ]; then
            printf "\nOK [$?]\n" >> mensaje.md
        else
            printf "\nNo OK [$?]\n" >> mensaje.md
        fi

        printf "\n#### cppcheck\n" >> mensaje.md

        printf "\n\`\`\`\n" >> mensaje.md

        cppcheck --suppress=missingIncludeSystem --language=c --enable=all $c_file >> mensaje.md 2>&1
        exit_status=$?
        printf "\n\`\`\`\n" >> mensaje.md
        if [ $exit_status -eq 0 ]; then
            printf "\nOK [$?]\n" >> mensaje.md
        else
            printf "\nNo OK [$?]\n" >> mensaje.md
        fi

        printf "\n#### splint\n" >> mensaje.md
        printf "\n\`\`\`\n" >> mensaje.md
        splint -hints +showscan +showalluses +stats -exportlocal $c_file >> mensaje.md 2>&1
        exit_status=$?
        printf "\n\`\`\`\n" >> mensaje.md
        if [ $exit_status -eq 0 ]; then
            printf "\nOK [$?]\n" >> mensaje.md
        else
            printf "\nNo OK [$?]\n" >> mensaje.md
        fi

        ##### Clang Toolchain (requiere de bear)
        printf "\n#### clang\n" >> mensaje.md
        printf "\n\`\`\`\n" >> mensaje.md
        bear  -- clang -Wall -Wextra $c_file  >> mensaje.md 2>&1
        exit_status=$?
        printf "\n\`\`\`\n" >> mensaje.md
        if [ $exit_status -eq 0 ]; then
            printf "\nOK [$?]\n" >> mensaje.md
        else
            printf "\nNo OK [$?]\n" >> mensaje.md
        fi

        printf "\n#### clang-tidy\n" >> mensaje.md
        printf "\n\`\`\`\n" >> mensaje.md
        clang-tidy -header-filter=.*  --config-file=tidy $c_file  >> mensaje.md 2>&1
        exit_status=$?
        printf "\n\`\`\`\n" >> mensaje.md
        if [ $exit_status -eq 0 ]; then
            printf "\nOK [$?]\n" >> mensaje.md
        else
            printf "\nNo OK [$?]\n" >> mensaje.md
        fi

    done    

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
