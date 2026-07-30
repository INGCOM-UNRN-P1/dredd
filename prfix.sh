#!/usr/bin/env bash
# Script para reconstruir el Pull Request de corrección

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
        echo "No se puede continuar, ha ocurrido un error al actualizar con git pull."
        exit 2
    fi

    echo "Reconstruyendo el PR..."
    git -C "$repo" reset --hard HEAD
    
    # Crear rama de correccion basada en el commit específico de base
    # NOTA: Asegurarse de que el hash del commit de origen exista o sea el HEAD de correccion
    base_commit="93cbbce0a84a46492662e505bd974fc1c4b07d46"
    
    if git -C "$repo" cat-file -e "$base_commit"^{commit} 2>/dev/null; then
        git -C "$repo" checkout -B correccion "$base_commit"
    else
        echo "Advertencia: El commit de base $base_commit no existe. Creando rama correccion desde HEAD."
        git -C "$repo" checkout -B correccion
    fi

    git -C "$repo" push -f --set-upstream origin correccion
    
    # Crear el Pull Request usando gh
    if command -v gh &> /dev/null; then
        gh pr create --repo "INGCOM-UNRN-P1/${estudiante_name}" --base main --head correccion --title "Corrección" --body "Pull Request de corrección automática" || true
    else
        echo "Error: gh (GitHub CLI) no está instalado para crear el PR."
    fi

else
    echo "Clonando el repositorio porque no existía..."
    git clone "https://github.com/INGCOM-UNRN-P1/${estudiante_name}.git" "$repo"
    echo "Ejecute el script nuevamente."
fi
