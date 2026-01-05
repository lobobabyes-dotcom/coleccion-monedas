@echo off
chcp 65001 >nul
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
set PGCLIENTENCODING=UTF8
set LC_ALL=C.UTF-8
set LANG=C.UTF-8

echo Iniciando aplicación de Colección de Monedas...
echo.
streamlit run app.py
