# Fichier: scripts/start_flask_server.ps1
# Ce script contient toute la logique pour démarrer le serveur.

# Aller à la racine du projet pour que tous les chemins relatifs fonctionnent
# $PSScriptRoot est une variable magique : le dossier où se trouve ce script.
Push-Location (Resolve-Path (Join-Path $PSScriptRoot ".."))

Write-Host "`n[SAMURAI] Current location set to project root: $(Get-Location)" -ForegroundColor Gray
Write-Host "[SAMURAI] Starting Backend Server..." -ForegroundColor Green

# Active l'environnement virtuel
try {
    . .\server\venv\Scripts\Activate.ps1
    Write-Host "[OK] Virtual environment activated." -ForegroundColor Cyan
} catch {
    Write-Host "[ERROR] Could not activate virtual environment. Make sure it exists at '.\server\venv\'" -ForegroundColor Red
    Read-Host -Prompt "Press Enter to exit"
    exit
}

# Définit les variables d'environnement
$env:FLASK_APP = "server:create_app()"
$env:FLASK_DEBUG = "1"
$env:DEBUG_METRICS = "1"
Write-Host "[OK] Flask environment variables set (FLASK_APP, FLASK_DEBUG, DEBUG_METRICS)." -ForegroundColor Cyan

# Lance le serveur
Write-Host "`nServer is running on http://localhost:5000" -ForegroundColor Yellow
Write-Host "Press CTRL+C to stop the server." -ForegroundColor Yellow
flask run --host=0.0.0.0 --port=5000

# Revenir à l'emplacement d'origine (bonne pratique)
Pop-Location