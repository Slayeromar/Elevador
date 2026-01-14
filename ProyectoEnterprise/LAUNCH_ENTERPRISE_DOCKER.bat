@echo off
title ENTERPRISE SYSTEM - DOCKER DEPLOY
echo ==========================================
echo    INICIANDO PLATAFORMA ENTERPRISE CES 2026
echo ==========================================
echo.
echo Verificando contenedores...
docker-compose up -d --build
echo.
echo ==========================================
echo    SISTEMA DESPLEGADO CORRECTAMENTE
echo.
echo  HMI WEB: http://localhost:8081  (Presione Ctrl+F5 si el login se queda pegado)
echo  GRAFANA: http://localhost:3000
echo  PROMETHEUS: http://localhost:9090
echo ==========================================
echo NOTA: Si ves errores de conexion, verifica que el API Gateway este en el puerto 8080.
pause
