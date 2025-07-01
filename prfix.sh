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

# el mensaje en el remote indica algo como
#https://github.com/INGCOM-UNRN-P1/tp3-2024-Ailu-G/pull/new/correccion
# para usar en los que no tienen ningún cambio

 
    echo "Reconstrucción del PR"

    git -C $repo reset --hard HEAD

    git -C $repo branch correccion 93cbbce0a84a46492662e505bd974fc1c4b07d46
    git -C $repo push --set-upstream origin correccion
    pushd .
    cd $repo
    gh -R INGCOM-UNRN-P1/$2 pr create -B correccion -t "Corrección" -b "Pull Request de correccion"
    popd

else
    echo "Clonando el repositorio si no lo estaba para $repo, ejecutar una segunda vez para verificar"
    echo "INGCOM-UNRN-P1/$2.git"
    git clone https://github.com/INGCOM-UNRN-P1/$2.git $repo



fi
