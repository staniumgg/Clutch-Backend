#!/usr/bin/env python3
"""
Script de inicio mejorado para Clutch eSports Bot
Incluye manejo robusto de errores WebSocket 4006
"""

import os
import sys
import asyncio
import logging
from datetime import datetime

def setup_logging():
    """Configura logging para mejor debugging."""
    # Crear directorio de logs si no existe
    os.makedirs('logs', exist_ok=True)
    
    # Configurar logging de Discord
    discord_logger = logging.getLogger('discord')
    discord_logger.setLevel(logging.WARNING)  # Solo warnings y errores
    
    # Handler para archivo
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_handler = logging.FileHandler(f'logs/bot_{timestamp}.log', encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    
    # Handler para consola
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.WARNING)
    
    # Formato
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(name)s %(message)s')
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    # Agregar handlers
    discord_logger.addHandler(file_handler)
    discord_logger.addHandler(console_handler)
    
    return discord_logger

def check_environment():
    """Verifica variables de entorno críticas."""
    print("🔍 Verificando configuración...")
    
    required_vars = [
        'DISCORD_TOKEN',
        'OPENAI_API_KEY',
        'AWS_REGION',
        'S3_BUCKET_NAME',
        'DYNAMODB_TABLE_NAME'
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print(f"❌ Variables de entorno faltantes: {', '.join(missing_vars)}")
        print("💡 Verifica tu archivo .env")
        return False
    
    print("✅ Todas las variables de entorno configuradas")
    return True

def check_dependencies():
    """Verifica dependencias críticas."""
    print("📦 Verificando dependencias...")
    
    try:
        import discord
        print(f"✅ discord.py: {discord.__version__}")
    except ImportError:
        print("❌ discord.py no instalado")
        return False
    
    try:
        import nacl
        print(f"✅ PyNaCl: {nacl.__version__}")
    except ImportError:
        print("❌ PyNaCl no instalado - Crítico para voz")
        print("💡 Instala con: pip install PyNaCl")
        return False
    
    # Opcional pero recomendado
    try:
        import discord.sinks
        print("✅ discord.sinks: Disponible (grabación automática)")
    except ImportError:
        print("⚠️ discord.sinks: No disponible (fallback manual OK)")
    
    return True

async def start_bot():
    """Inicia el bot con manejo mejorado de errores."""
    from dotenv import load_dotenv
    load_dotenv()
    
    # Configurar logging
    logger = setup_logging()
    
    print("🎧 CLUTCH ESPORTS BOT - INICIO MEJORADO")
    print("=" * 50)
    
    # Verificaciones pre-inicio
    if not check_environment():
        return False
    
    if not check_dependencies():
        return False
    
    # Importar y configurar bot
    try:
        import esports
        print("✅ Módulo esports importado correctamente")
    except Exception as e:
        print(f"❌ Error importando esports: {e}")
        return False
    
    # Configurar el bot para manejar mejor las conexiones
    print("\n🔧 CONFIGURACIÓN ANTI-ERROR 4006:")
    print("• Reconexión automática: DESHABILITADA")
    print("• Timeout extendido: 15 segundos")
    print("• Manejo específico de error 4006")
    print("• Fallback manual siempre disponible")
    
    print("\n🎮 COMANDOS DISPONIBLES:")
    print("   🎙️ !record → Iniciar grabación")
    print("   ⏹️ !stop → Terminar y procesar")
    print("   🔍 !diagnostico → Diagnóstico completo")
    print("   🔧 !permisos → Verificar permisos")
    print("   🧪 !test_conexion → Probar conexión")
    print("   📊 !status → Estado del bot")
    print("   🔌 !disconnect → Desconectar (emergencia)")
    
    # Iniciar bot
    try:
        discord_token = os.getenv("DISCORD_TOKEN")
        if not discord_token:
            print("❌ DISCORD_TOKEN no encontrado")
            return False
        
        print("\n🚀 Iniciando bot...")
        print("💡 Logs detallados en: logs/")
        print("🔧 Si hay error 4006: usa !diagnostico")
        
        # El bot se ejecuta desde esports.py
        return True
        
    except Exception as e:
        print(f"❌ Error iniciando bot: {e}")
        logger.exception("Error fatal iniciando bot")
        return False

if __name__ == "__main__":
    print("🤖 CLUTCH ESPORTS - LAUNCHER ANTI-ERROR 4006")
    
    # Verificar Python
    if sys.version_info < (3, 8):
        print("❌ Requiere Python 3.8 o superior")
        sys.exit(1)
    
    # Cambiar al directorio del script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    print(f"📁 Directorio: {script_dir}")
    
    # Ejecutar verificaciones
    success = asyncio.run(start_bot())
    
    if success:
        print("\n✅ Verificaciones completadas. Iniciando bot...")
        print("🔄 Ejecutando: python esports.py")
        
        # Ejecutar el bot real
        try:
            import subprocess
            result = subprocess.run([sys.executable, "esports.py"], cwd=script_dir)
            print(f"\n🏁 Bot terminado con código: {result.returncode}")
        except KeyboardInterrupt:
            print("\n⏹️ Bot detenido por usuario")
        except Exception as e:
            print(f"\n❌ Error ejecutando bot: {e}")
    else:
        print("\n❌ Verificaciones fallaron. No se puede iniciar el bot.")
        print("💡 Revisa los errores arriba y corrige la configuración.")
        sys.exit(1)
