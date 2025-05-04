@echo off
:: Lancement via l'Anaconda Prompt
start "" "%USERPROFILE%\anaconda3\Scripts\activate.bat" ia_camembert && ^
cmd /k "cd /d %~dp0 && python src\app.py"
