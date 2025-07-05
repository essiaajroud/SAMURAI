@echo off
cd /d %~dp0
call venv\Scripts\activate
pip install flask flask_sqlalchemy flask_cors
