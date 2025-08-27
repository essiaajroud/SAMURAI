@echo off
echo 🎯 Installation et Configuration du Serveur
echo ================================================

REM Vérifier si Python est installé
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python n'est pas installé ou n'est pas dans le PATH
    pause
    exit /b 1
)

REM Vérifier si app.py existe
if not exist "app.py" (
    echo ❌ Fichier app.py non trouvé. Exécutez ce script depuis le dossier server/
    pause
    exit /b 1
)

REM Créer l'environnement virtuel s'il n'existe pas
if not exist "venv" (
    echo 📦 Création de l'environnement virtuel...
    python -m venv venv
    if errorlevel 1 (
        echo ❌ Erreur lors de la création de l'environnement virtuel
        pause
        exit /b 1
    )
    echo ✅ Environnement virtuel créé
) else (
    echo ✅ Environnement virtuel existant
)

REM Installer les dépendances
echo 📦 Installation des dépendances...
call venv\Scripts\activate
pip install -r requirements.txt
if errorlevel 1 (
    echo ❌ Erreur lors de l'installation des dépendances
    pause
    exit /b 1
)
echo ✅ Dépendances installées

REM Démarrer le serveur avec la méthode FLASK RUN
echo 🚀 Démarrage du serveur Flask avec la méthode correcte...
echo 📍 Serveur accessible sur: http://localhost:5000
echo 📊 API disponible sur: http://localhost:5000/api
echo 🔍 Health check: http://localhost:5000/api/health
echo.
echo ⏹️  Appuyez sur Ctrl+C pour arrêter le serveur
echo.

rem Définir les variables et lancer via flask run
set FLASK_APP=server.app
set FLASK_DEBUG=1
flask run --host=0.0.0.0 --port=5000

echo.
echo 🛑 Serveur arrêté
pause