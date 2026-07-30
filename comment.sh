#!/usr/bin/env bash
# Script para enviar comentarios de corrección al PR en GitHub

set -euo pipefail

if [ "$#" -ne 1 ]; then
    echo "Uso: $0 <nombre-estudiante>"
    exit 1
fi

estudiante_name="$1"
reporte_file="${estudiante_name}.md"

echo "Procesando comentarios de corrección para ${estudiante_name}..."

if [ -f "$reporte_file" ]; then
    if ! command -v gh &> /dev/null; then
        echo "Error: gh (GitHub CLI) no está instalado."
        exit 3
    fi

    pr_url="https://github.com/INGCOM-UNRN-P1/${estudiante_name}/pull/1"
    
    echo "Enviando comentario al PR: ${pr_url}..."
    if gh pr comment "$pr_url" -F "$reporte_file"; then
        echo "Comentario enviado con éxito."
    else
        echo "Error al enviar el comentario."
    fi

    # Intentar abrir la url del PR en el navegador
    if command -v xdg-open &> /dev/null; then
        xdg-open "${pr_url}/files" &> /dev/null &
    elif command -v firefox &> /dev/null; then
        firefox -new-tab "${pr_url}/files" &> /dev/null &
    fi
else
    echo "El reporte '${reporte_file}' no fue encontrado."
    echo "Parece que el análisis no se ha ejecutado aún."
fi
