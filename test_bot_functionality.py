#!/usr/bin/env python3
"""
Script de prueba para verificar la funcionalidad del bot Clutch eSports
"""

import sys
import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

def test_imports():
    """Prueba que todas las importaciones funcionen."""
    print("🧪 Probando importaciones...")
    
    try:
        import discord
        print(f"   ✅ discord.py: {discord.__version__}")
    except ImportError as e:
        print(f"   ❌ discord.py: {e}")
        return False
    
    try:
        import requests
        print(f"   ✅ requests: {requests.__version__}")
    except ImportError as e:
        print(f"   ❌ requests: {e}")
        return False
    
    try:
        from google.cloud import texttospeech
        print("   ✅ google-cloud-texttospeech")
    except ImportError as e:
        print(f"   ❌ google-cloud-texttospeech: {e}")
        return False
    
    try:
        import mutagen
        print(f"   ✅ mutagen: {mutagen.version_string}")
    except ImportError as e:
        print(f"   ❌ mutagen: {e}")
        return False
    
    return True

def test_env_variables():
    """Prueba que las variables de entorno estén configuradas."""
    print("\n🧪 Probando variables de entorno...")
    
    required_vars = [
        "DISCORD_TOKEN",
        "OPENAI_API_KEY",
        "AWS_ACCESS_KEY_ID",
        "AWS_SECRET_ACCESS_KEY",
        "AWS_REGION",
        "S3_BUCKET_NAME",
        "DYNAMODB_TABLE_NAME"
    ]
    
    all_present = True
    for var in required_vars:
        value = os.getenv(var)
        if value:
            # Mostrar solo los primeros caracteres por seguridad
            display_value = value[:8] + "..." if len(value) > 8 else value
            print(f"   ✅ {var}: {display_value}")
        else:
            print(f"   ❌ {var}: No configurada")
            all_present = False
    
    return all_present

def test_discord_functionality():
    """Prueba funcionalidad básica de Discord."""
    print("\n🧪 Probando funcionalidad de Discord...")
    
    try:
        import discord
        from discord.ext import commands
        
        # Crear intents
        intents = discord.Intents.default()
        intents.message_content = True
        intents.voice_states = True
        print("   ✅ Intents configurados correctamente")
        
        # Crear bot básico
        bot = commands.Bot(command_prefix="!", intents=intents)
        print("   ✅ Bot creado correctamente")
        
        # Verificar si discord.sinks está disponible
        try:
            import discord.sinks
            print("   ✅ discord.sinks disponible (grabación automática)")
        except ImportError:
            print("   ⚠️ discord.sinks no disponible (usar modo fallback)")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Error en funcionalidad Discord: {e}")
        return False

def test_aws_imports():
    """Prueba importaciones de AWS."""
    print("\n🧪 Probando funcionalidad AWS...")
    
    try:
        from dynamodb_config import save_analysis_complete
        print("   ✅ dynamodb_config importado")
    except ImportError as e:
        print(f"   ❌ dynamodb_config: {e}")
        return False
    
    try:
        import boto3
        print(f"   ✅ boto3 disponible")
    except ImportError as e:
        print(f"   ❌ boto3: {e}")
        return False
    
    return True

def main():
    """Ejecuta todas las pruebas."""
    print("🎧 CLUTCH ESPORTS BOT - PRUEBAS DE FUNCIONALIDAD")
    print("=" * 50)
    
    tests = [
        ("Importaciones", test_imports),
        ("Variables de entorno", test_env_variables),
        ("Funcionalidad Discord", test_discord_functionality),
        ("Funcionalidad AWS", test_aws_imports)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append(result)
        except Exception as e:
            print(f"   ❌ Error en {test_name}: {e}")
            results.append(False)
    
    print("\n" + "=" * 50)
    print("📊 RESUMEN DE PRUEBAS:")
    
    for i, (test_name, _) in enumerate(tests):
        status = "✅ PASÓ" if results[i] else "❌ FALLÓ"
        print(f"   {test_name}: {status}")
    
    total_passed = sum(results)
    total_tests = len(tests)
    
    print(f"\n🎯 RESULTADO: {total_passed}/{total_tests} pruebas pasaron")
    
    if total_passed == total_tests:
        print("\n🚀 ¡BOT LISTO PARA USAR!")
        print("   Ejecuta: python esports.py")
    else:
        print("\n⚠️ CORREGE LOS ERRORES ANTES DE USAR EL BOT")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
