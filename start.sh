#!/data/data/com.termux/files/usr/bin/bash

set -e

if [ -f .env ]; then
    set -a
    . ./.env
    set +a
else
    echo "ERROR: .env not found."
    echo "Copy .env.example to .env and configure it first."
    exit 1
fi

echo "Starting Accountant AI Agent..."
exec uvicorn api.main:app --host "${HOST:-127.0.0.1}" --port "${PORT:-8000}"
