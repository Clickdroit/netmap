@echo off
title Net-Map - Scanner de Reseau et Topologie
chcp 65001 >nul
cls

echo ========================================================
echo        Net-Map • Scanner Réseau & Topologie
echo ========================================================
echo.

if not exist ".venv" (
    echo [*] Création de l'environnement virtuel Python...
    python -m venv .venv
    echo [*] Installation des dépendances...
    .\.venv\Scripts\pip install -r requirements.txt
)

echo [*] Démarrage de l'application...
.\.venv\Scripts\python main.py

pause
