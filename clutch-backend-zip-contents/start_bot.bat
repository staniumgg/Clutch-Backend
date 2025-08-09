@echo off
echo 🤖 CLUTCH ESPORTS BOT - INICIADOR ROBUSTO
echo ===============================================
echo.

echo 🔍 Verificando dependencias...
python verify_dependencies.py
if %ERRORLEVEL% NEQ 0 (
    echo ❌ Error en verificación de dependencias
    pause
    exit /b 1
)

echo.
echo 🚀 Iniciando bot Discord...
echo 💡 Usa Ctrl+C para detener el bot
echo.
echo 🎧 COMANDOS DISPONIBLES:
echo    !record          - Iniciar grabación
echo    !stop            - Terminar y analizar
echo    !diagnostico     - Verificar sistema completo
echo    !permisos        - Verificar permisos de voz
echo    !test_conexion   - Probar conexión
echo    !info            - Información del bot
echo.
echo ⚠️  Si hay error WebSocket 4006, usa !diagnostico
echo.

python esports.py
