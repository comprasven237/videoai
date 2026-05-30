@echo off
REM VIDEOAI - Script de construcción para Windows (.exe)

echo 🎬 Construyendo VIDEOAI para Windows
echo ==================================================

REM Verificar Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Error: Python no está instalado o no está en PATH
    echo Descarga Python desde https://python.org
    pause
    exit /b 1
)

REM Crear entorno virtual si no existe
if not exist "venv" (
    echo 📦 Creando entorno virtual...
    python -m venv venv
)

REM Activar entorno virtual
echo 🔌 Activando entorno virtual...
call venv\Scripts\activate.bat

REM Instalar/actualizar dependencias
echo 📥 Instalando dependencias...
pip install -r requirements.txt --quiet
pip install pyinstaller --quiet

REM Limpiar construcciones anteriores
echo 🧹 Limpiando...
if exist "dist" rmdir /s /q dist
if exist "build" rmdir /s /q build
if exist "VIDEOAI.spec" del /q VIDEOAI.spec

REM Crear spec file
echo 📝 Creando configuración de PyInstaller...
pyi-makespec --onefile --windowed --name VIDEOAI launcher.py

REM Editar spec file para incluir todos los archivos
echo ⚙️  Configurando archivos adicionales...

REM Construir executable
echo 🔨 Construyendo executable...
pyinstaller VIDEOAI.spec

REM Verificar resultado
if exist "dist\VIDEOAI.exe" (
    echo.
    echo ✅ ¡Construcción completada!
    echo ==========================================
    echo Executable creado: dist\VIDEOAI.exe
    echo.
    echo Para crear instalador con Inno Setup:
    echo   1. Instalar Inno Setup desde https://jrsoftware.org/isdl.php
    echo   2. Abrir installer.iss con Inno Setup
    echo   3. Compilar el instalador
    echo.
    echo Para ejecutar directamente:
    echo   dist\VIDEOAI.exe
    echo.
) else (
    echo ❌ Error: No se pudo crear el executable
    echo Revisa los mensajes de error arriba
    pause
    exit /b 1
)

REM Desactivar entorno virtual
deactivate

pause
