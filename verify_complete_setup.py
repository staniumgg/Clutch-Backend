# Script de verificación final para el bot con comandos !record y !stop
import os
import sys
from dotenv import load_dotenv

def verify_complete_setup():
    """Verifica que el setup completo esté funcionando con grabación de voz."""
    
    print("🎮 VERIFICACIÓN FINAL - CLUTCH ESPORTS BOT")
    print("=" * 60)
    print("📅 Fecha:", "28 de Julio, 2025")
    print("🎯 Versión: Cloud-Only con Grabación de Voz")
    print("=" * 60)
    
    # Cargar variables de entorno
    load_dotenv()
    
    # 1. Verificar variables AWS
    print("\n🔧 1. CONFIGURACIÓN AWS:")
    aws_vars = {
        'AWS_ACCESS_KEY_ID': os.getenv('AWS_ACCESS_KEY_ID'),
        'AWS_SECRET_ACCESS_KEY': os.getenv('AWS_SECRET_ACCESS_KEY'), 
        'AWS_REGION': os.getenv('AWS_REGION'),
        'S3_BUCKET_NAME': os.getenv('S3_BUCKET_NAME'),
        'DYNAMODB_TABLE_NAME': os.getenv('DYNAMODB_TABLE_NAME')
    }
    
    aws_complete = True
    for var, value in aws_vars.items():
        status = "✅" if value else "❌"
        if not value:
            aws_complete = False
        region_info = f" ({value})" if var == 'AWS_REGION' and value else ""
        bucket_info = f" ({value})" if var == 'S3_BUCKET_NAME' and value else ""
        print(f"   {status} {var}{region_info}{bucket_info}")
    
    # 2. Verificar APIs
    print("\n🔑 2. CONFIGURACIÓN DE APIs:")
    api_vars = {
        'OPENAI_API_KEY': os.getenv('OPENAI_API_KEY'),
        'DISCORD_TOKEN': os.getenv('DISCORD_TOKEN'),
        'GOOGLE_APPLICATION_CREDENTIALS': os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
    }
    
    api_complete = True
    for var, value in api_vars.items():
        status = "✅" if value else "❌"
        if not value:
            api_complete = False
        print(f"   {status} {var}")
    
    # 3. Verificar archivos esenciales
    print("\n📁 3. ARCHIVOS ESENCIALES:")
    essential_files = {
        'esports.py': 'Bot principal con grabación',
        'dynamodb_config.py': 'Configuración DynamoDB + S3',
        's3_config.py': 'Configuración S3',
        '.env': 'Variables de entorno'
    }
    
    files_complete = True
    for file, desc in essential_files.items():
        exists = os.path.exists(file)
        status = "✅" if exists else "❌"
        if not exists:
            files_complete = False
        print(f"   {status} {file} - {desc}")
    
    # 4. Verificar características del bot
    print("\n🤖 4. CARACTERÍSTICAS DEL BOT:")
    try:
        with open('esports.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        features = {
            'Comando !record': '@bot.command(name=\'record\')' in content,
            'Comando !stop': '@bot.command(name=\'stop\')' in content,
            'Grabación de voz': 'start_recording' in content,
            'Procesamiento cloud': 'save_analysis_complete' in content,
            'TTS en memoria': 'generate_tts_audio_to_bytes' in content,
            'Subida de archivos': 'process_audio_attachment' in content,
            'Sin archivos locales': content.count('recordings/') <= 2  # Solo referencias mínimas
        }
        
        bot_complete = True
        for feature, check in features.items():
            status = "✅" if check else "❌"
            if not check:
                bot_complete = False
            print(f"   {status} {feature}")
            
    except Exception as e:
        print(f"   ❌ Error leyendo esports.py: {e}")
        bot_complete = False
    
    # 5. Verificar dependencias
    print("\n📦 5. DEPENDENCIAS DE PYTHON:")
    try:
        # Verificar imports principales
        imports = {
            'discord': 'Discord.py con soporte de voz',
            'boto3': 'AWS SDK',
            'openai': 'OpenAI API',
            'google.cloud.texttospeech': 'Google TTS',
            'requests': 'HTTP requests',
            'asyncio': 'Async support'
        }
        
        deps_complete = True
        for module, desc in imports.items():
            try:
                __import__(module)
                print(f"   ✅ {module} - {desc}")
            except ImportError:
                print(f"   ❌ {module} - {desc} (NO INSTALADO)")
                deps_complete = False
                
    except Exception as e:
        print(f"   ❌ Error verificando dependencias: {e}")
        deps_complete = False
    
    # 6. Resumen y instrucciones
    print("\n" + "=" * 60)
    print("📊 RESUMEN FINAL:")
    
    overall_status = aws_complete and api_complete and files_complete and bot_complete and deps_complete
    
    if overall_status:
        print("   🎉 ¡CONFIGURACIÓN COMPLETAMENTE LISTA!")
        print("   ✅ El bot funciona en modo Cloud-Only con grabación de voz")
        
        print("\n🚀 PARA EJECUTAR EL BOT:")
        print("   python esports.py")
        
        print("\n🎮 CÓMO USAR:")
        print("   1. Ejecuta el bot con el comando de arriba")
        print("   2. En Discord, únete a un canal de voz")
        print("   3. Escribe !record (el bot se une y graba)")
        print("   4. Habla normalmente durante tu partida")
        print("   5. Escribe !stop (procesa y analiza)")
        print("   6. Recibe feedback personalizado por audio")
        
        print("\n📱 COMANDOS DISPONIBLES:")
        print("   • !record - Iniciar grabación en canal de voz")
        print("   • !stop - Terminar grabación y analizar")
        print("   • !preferencias - Restablecer configuración")
        print("   • !info - Información del bot")
        print("   • Subir MP3/WAV - Método alternativo")
        
        print("\n☁️ ALMACENAMIENTO:")
        print(f"   • S3: {aws_vars.get('S3_BUCKET_NAME', 'N/A')} (audios)")
        print(f"   • DynamoDB: {aws_vars.get('DYNAMODB_TABLE_NAME', 'N/A')} (análisis)")
        print(f"   • Región: {aws_vars.get('AWS_REGION', 'N/A')}")
        
    else:
        print("   ⚠️ CONFIGURACIÓN INCOMPLETA")
        if not aws_complete:
            print("   ❌ Faltan configuraciones de AWS")
        if not api_complete:
            print("   ❌ Faltan claves de APIs")
        if not files_complete:
            print("   ❌ Faltan archivos esenciales")
        if not bot_complete:
            print("   ❌ El bot no tiene todas las características")
        if not deps_complete:
            print("   ❌ Faltan dependencias de Python")
    
    print("\n" + "=" * 60)
    print("🎯 CLUTCH ESPORTS - ANÁLISIS DE COMUNICACIÓN EN CLOUD")
    print("🏆 ¡Ready para mejorar tu comunicación en eSports!")
    print("=" * 60)
    
    return overall_status

if __name__ == "__main__":
    verify_complete_setup()
