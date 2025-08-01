@echo off
chcp 65001 >nul
echo 🚀 Démarrage automatique du streaming SAMURAI
echo ================================================

REM Vérifier si l'environnement virtuel existe
if not exist "venv\Scripts\activate.bat" (
    echo ❌ Environnement virtuel non trouvé
    echo 🔧 Création de l'environnement virtuel...
    python -m venv venv
    if errorlevel 1 (
        echo ❌ Erreur lors de la création de l'environnement virtuel
        pause
        exit /b 1
    )
)

REM Activer l'environnement virtuel
echo 🔧 Activation de l'environnement virtuel...
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo ❌ Erreur lors de l'activation de l'environnement virtuel
    pause
    exit /b 1
)

REM Installer les dépendances si nécessaire
echo 📦 Vérification des dépendances...
pip install requests >nul 2>&1
if errorlevel 1 (
    echo ⚠️ Installation de requests...
    pip install requests
)

REM Attendre que le serveur soit prêt
echo ⏳ Attente du serveur Flask...
timeout /t 3 /nobreak >nul

REM Démarrer le streaming automatiquement
echo 🎬 Démarrage du streaming...
python start_stream_auto.py

if errorlevel 1 (
    echo.
    echo ❌ Échec du démarrage du streaming
    echo.
    echo 🔧 Solutions possibles:
    echo    1. Vérifiez que le serveur Flask est en cours d'exécution
    echo    2. Vérifiez que YOLO est correctement configuré
    echo    3. Vérifiez qu'il y a des vidéos dans le dossier videos/
    echo.
    echo 💡 Pour démarrer le serveur Flask:
    echo    python app.py
    echo.
    pause
) else (
    echo.
    echo ✅ Streaming démarré avec succès!
    echo 🌐 Interface web: http://localhost:3000
    echo 📹 Flux vidéo: http://localhost:5000/video_feed
    echo.
    echo 💡 Appuyez sur Ctrl+C pour arrêter le streaming
    echo.
)

pause 