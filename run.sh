#!/usr/bin/env bash
# Net-Map - Network Scanner & Topology Map for Linux / WSL

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "========================================================"
echo "    Net-Map • Scanner Réseau & Topologie (Linux / WSL)  "
echo "========================================================"
echo ""

if [ ! -d ".venv-linux" ]; then
    echo "[*] Configuration de l'environnement virtuel Linux..."
    if command -v virtualenv >/dev/null 2>&1; then
        virtualenv .venv-linux
    elif [ -f "$HOME/.local/bin/virtualenv" ]; then
        "$HOME/.local/bin/virtualenv" .venv-linux
    else
        python3 -m venv .venv-linux
    fi
    echo "[*] Installation des dépendances..."
    ./.venv-linux/bin/pip install -r requirements.txt
fi

echo "[*] Démarrage du serveur Net-Map..."
./.venv-linux/bin/python main.py
