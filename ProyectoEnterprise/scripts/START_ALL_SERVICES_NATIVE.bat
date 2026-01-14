@echo off
title ENTERPRISE SYSTEM - NATIVE RUN (NO DOCKER)
echo ==========================================
echo    INICIANDO SERVICIOS EN MODO NATIVO
echo ==========================================
echo.

echo [1/5] Iniciando PLC SERVICE (Puerto 8000)...
start /B cmd /c "python services\plc-service\main.py"
timeout /t 2

echo [2/5] Iniciando AUTH SERVICE (Puerto 8001)...
start /B cmd /c "python services\auth-service\main.py"
timeout /t 1

echo [3/5] Iniciando ALARM SERVICE (Puerto 8002)...
start /B cmd /c "python services\alarm-service\main.py"
timeout /t 1

echo [4/5] Iniciando HISTORIAN SERVICE (Puerto 8003)...
start /B cmd /c "python services\historian-service\main.py"
timeout /t 1

echo [5/5] Iniciando API GATEWAY (Puerto 8080)...
start /B cmd /c "python services\api-gateway\main.py"

echo.
echo ==========================================
echo    SISTEMA LISTO (SERVIDOR INTERNO)
echo.
echo  PANELES ACTIVOS:
echo  HMI WEB: Abre el archivo hmi/web-app/index.html
echo  STATUS: http://127.0.0.1:8080/plc/state
echo ==========================================
echo Presiona CTRL+C para detener todo.
pause
