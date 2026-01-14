@echo off
TITLE Enterprise Elevator System - Ultra Fix Launcher
COLOR 0B

echo =========================================================
echo    ENTERPRISE INDUSTRIAL SYSTEM - INSTALLER v2.0
echo =========================================================
echo.

echo [+] Instalando libreria de red central (httpx)...
python -m pip install httpx --quiet

echo [+] Instalando libreria de control industrial (snap7)...
python -m pip install python-snap7 --quiet

echo [+] Instalando servidor web y seguridad (fastapi, jose, etc)...
python -m pip install fastapi uvicorn paho-mqtt python-jose passlib --quiet

echo.
echo [+] Verificando modulos criticos...
python -c "import httpx; print('   - httpx: OK')" || echo ❌ Error en httpx
python -c "import snap7; print('   - snap7: OK')" || echo ❌ Error en snap7

echo.
echo [+] Iniciando servicios en cascada...
echo.

echo [1/4] PLC SERVICE...
start "PLC_SERVICE" cmd /k "cd services/plc-service && python main.py"

echo [2/4] ALARM SERVICE...
start "ALARM_SERVICE" cmd /k "cd services/alarm-service && python main.py"

echo [3/4] AUTH SERVICE...
start "AUTH_SERVICE" cmd /k "cd services/auth-service && python main.py"

echo [4/4] API GATEWAY...
start "API_GATEWAY" cmd /k "cd services/api-gateway && python main.py"

echo.
echo ---------------------------------------------------------
echo [!] ARQUITECTURA DESPLEGADA
echo [!] Si las ventanas dicen "Uvicorn running", ya puedes abrir el HMI.
echo ---------------------------------------------------------
echo.
pause
