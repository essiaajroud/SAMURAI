@echo off
rem Ce script lance le script de logique PowerShell. Il doit être à la racine du projet.

echo [SAMURAI] Launching PowerShell start script...

rem Le chemin 'scripts\start_flask_server.ps1' est relatif à cet emplacement (la racine).
powershell -ExecutionPolicy Bypass -File "scripts\start_flask_server.ps1"

echo.
echo [SAMURAI] Server script finished.
pause