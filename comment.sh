#!/usr/bin/bash

echo "Procesando comentarios de corrección para $1"

if [ -f "$1.md" ]; then
    gh pr comment https://github.com/INGCOM-UNRN-P1/$1/pull/1 -F $1.md
    #firefox -new-tab -url "https://github.com/INGCOM-UNRN-PII/$1/pull/1/files" -new-tab -url "``"
else
    echo "El reporte '$1.md' no fue encontrado"
    echo "Parece que dredd no pasó por acá aún."
fi
