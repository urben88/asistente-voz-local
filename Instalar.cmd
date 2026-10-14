@echo off
setlocal EnableExtensions
title Asistente de voz local - Instalador

rem Instalador en 1 clic - Asistente de voz local (Handy + Ollama)
rem Doble clic para instalar todo. Windows pedira permisos de administrador (UAC).
rem Opciones extra: pasa los mismos argumentos que install.ps1 (-Simular, -AsistenteModelo, -NoAbrir).

set "PS1=%~dp0scripts\install.ps1"

if not exist "%PS1%" (
    echo ERROR: no se encuentra "%PS1%"
    echo Copia la carpeta completa del repositorio y vuelve a intentarlo.
    pause
    exit /b 1
)

rem -Simular no necesita permisos: no instala, no descarga y no toca nada
set "SIMULA="
echo %* | find /i "-Simular" >nul 2>&1
if not errorlevel 1 set "SIMULA=1"

if defined SIMULA goto instalar

rem Si ya somos administradores (nivel de integridad alto), instalamos directamente
whoami /groups | findstr /i "S-1-16-12288" >nul 2>&1
if not errorlevel 1 goto instalar

rem Relanzar como administrador (UAC) y salir: la instalacion sigue en la ventana nueva
echo Se necesitan permisos de administrador para instalar Handy y Ollama.
echo Windows mostrara un aviso: pulsa "Si".
set "ARGS="
if not "%*"=="" set "ARGS=-ArgumentList '%*'"
powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Process -Verb RunAs -FilePath '%~f0' %ARGS%"
if errorlevel 1 (
    echo.
    echo No se han concedido los permisos de administrador: no se ha instalado nada.
    pause
    exit /b 1
)
exit /b 0

:instalar
powershell -NoProfile -ExecutionPolicy Bypass -File "%PS1%" %*
set "RC=%ERRORLEVEL%"
echo.
if not "%RC%"=="0" echo El instalador ha terminado con el codigo %RC%. Revisa los avisos de arriba.
pause
exit /b %RC%
