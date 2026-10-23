#!/usr/bin/env bash

if pgrep -x "anki" > /dev/null 2>&1; then
    echo "Anki is already running."
else
    echo "Anki is not running. Starting now..."
    nohup anki > /dev/null 2>&1 &
    sleep 2
fi

python3 "../textgenanki.py"
read -p "Enter to close"
