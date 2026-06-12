@echo off
python src\silver.py
if errorlevel 1 exit /b 1
python src\pesos.py
if errorlevel 1 exit /b 1
python src\elo.py
if errorlevel 1 exit /b 1
python src\gold.py
if errorlevel 1 exit /b 1
python src\treino.py
if errorlevel 1 exit /b 1
echo Pipeline concluido com sucesso!
