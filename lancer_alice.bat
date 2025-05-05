@echo off
%WINDIR%\System32\WindowsPowerShell\v1.0\powershell.exe -ExecutionPolicy ByPass -NoExit -Command ^
"& 'C:\Users\Blazufr\anaconda3\shell\condabin\conda-hook.ps1'; ^
conda activate ia_camembert; ^
python 'C:\Users\Blazufr\Desktop\IA_alice_V3\src\app.py'"
