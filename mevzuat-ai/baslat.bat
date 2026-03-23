@echo off
chcp 65001 >nul
title Mevzuat AI

echo.
echo  ⚖️  Mevzuat AI Baslatiliyor...
echo  ──────────────────────────────
echo.

REM Check Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo  ❌ Python bulunamadi!
    echo  Lutfen https://www.python.org/downloads/ adresinden Python yukleyin.
    echo  Kurulumda "Add Python to PATH" secenegini isaretlemeyi unutmayin.
    pause
    exit /b 1
)

REM Install dependencies if needed
if not exist ".venv" (
    echo  📦 Ilk kurulum yapiliyor...
    python -m venv .venv
    call .venv\Scripts\activate.bat
    pip install -r requirements.txt --quiet
    echo  ✅ Kurulum tamamlandi.
) else (
    call .venv\Scripts\activate.bat
)

echo  ✅ Tarayicinizda aciliyor...
echo  Kapatmak icin bu pencereyi kapatin veya Ctrl+C basin.
echo.

streamlit run app.py --server.headless true --browser.gatherUsageStats false
