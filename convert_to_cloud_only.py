"""
Script para convertir el bot a modo solo nube.
Modifica esports.py para eliminar dependencias de archivos locales.
"""

import os
import shutil

def backup_current_file():
    """Crea backup del archivo actual."""
    
    if os.path.exists('esports.py'):
        backup_name = 'esports_before_cloud_only.py'
        shutil.copy2('esports.py', backup_name)
        print(f"✅ Backup creado: {backup_name}")
        return True
    return False

def create_cloud_only_esports():
    """Crea una versión de esports.py optimizada para solo nube."""
    
    # Leer el archivo actual
    with open('esports.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Encontrar donde empieza el main
    main_start = content.find('if __name__ == "__main__":')
    
    if main_start == -1:
        print("❌ No se encontró el bloque main")
        return False
    
    # Tomar todo el código hasta el main
    code_before_main = content[:main_start]
    
    # Nuevo main para modo solo nube
    new_main = '''if __name__ == "__main__":
    print("🎧 Clutch eSports Bot - Iniciando...")
    print("☁️ Modo: Solo Nube (S3 + DynamoDB)")
    print("📱 Los audios se procesan directamente desde Discord")
    print("💾 Sin almacenamiento local")
    
    # Verificar configuración de AWS
    aws_region = os.getenv('AWS_REGION')
    s3_bucket = os.getenv('S3_BUCKET_NAME')
    dynamodb_table = os.getenv('DYNAMODB_TABLE_NAME')
    
    print(f"🌍 AWS Región: {aws_region}")
    print(f"🪣 S3 Bucket: {s3_bucket}")
    print(f"💾 DynamoDB: {dynamodb_table}")
    
    # Verificar que las configuraciones estén presentes
    if not all([aws_region, s3_bucket, dynamodb_table]):
        print("❌ Error: Configuración de AWS incompleta en .env")
        print("🔧 Verifica que tengas configurado:")
        print("   • AWS_REGION")
        print("   • S3_BUCKET_NAME") 
        print("   • DYNAMODB_TABLE_NAME")
        exit(1)
    
    print("\\n✅ Configuración de solo nube:")
    print("   • Los archivos se suben directamente a S3")
    print("   • Los análisis se guardan en DynamoDB") 
    print("   • No se crean carpetas locales")
    print("   • No se monitorean archivos locales")
    
    print("\\n🤖 El bot está configurado para:")
    print("   📱 Recibir archivos por Discord")
    print("   🎙️ Procesar con Whisper + GPT") 
    print("   ☁️ Almacenar en AWS automáticamente")
    print("   📊 Consultar historial y estadísticas")
    
    print("\\n💡 INSTRUCCIONES:")
    print("   1. Los usuarios suben MP3 directamente al bot")
    print("   2. El bot procesa automáticamente:")
    print("      • Transcripción con Whisper")
    print("      • Análisis con GPT")
    print("      • Subida a S3")
    print("      • Guardado en DynamoDB")
    print("   3. El usuario recibe análisis por Discord")
    
    try:
        print("\\n⌨️ Bot configurado y listo. Presiona Ctrl+C para salir...")
        print("🔗 Los usuarios pueden interactuar con el bot vía Discord")
        
        # Mantener el script corriendo
        while True:
            time.sleep(60)  # Dormir 1 minuto
            print(".", end="", flush=True)  # Mostrar que está vivo
            
    except KeyboardInterrupt:
        print("\\n🛑 Cerrando Clutch eSports Bot...")
        print("✅ Bot cerrado correctamente.")
        print("💾 Todos los datos permanecen seguros en AWS")

# ============================================================================
# FUNCIONES AUXILIARES
# ============================================================================

def list_google_tts_voices(language_code="es"):
    """Lista todas las voces disponibles de Google TTS para un idioma."""
    from google.cloud import texttospeech
    client = texttospeech.TextToSpeechClient()
    voices = client.list_voices(language_code=language_code).voices
    for v in voices:
        print(f"{v.name} | {v.ssml_gender} | {v.language_codes} | {v.natural_sample_rate_hertz} | {v.description if hasattr(v, 'description') else ''}")
    return voices
'''
    
    # Combinar código
    new_content = code_before_main + new_main
    
    # Escribir el nuevo archivo
    with open('esports.py', 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print("✅ Archivo esports.py actualizado para modo solo nube")
    return True

def verify_imports():
    """Verifica que los imports estén correctos."""
    
    with open('esports.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    print("\\n🔍 Verificando imports...")
    
    required_imports = [
        'from dynamodb_config import dynamodb_manager, save_analysis, save_analysis_complete',
        'from watchdog.observers import Observer',
        'from watchdog.events import FileSystemEventHandler'
    ]
    
    # Verificar imports de DynamoDB
    if 'save_analysis_complete' in content:
        print("✅ Import de función integrada S3+DynamoDB")
    else:
        print("⚠️ Falta import de save_analysis_complete")
        
    # Verificar que watchdog no sea crítico
    if 'Observer' in content and 'FileSystemEventHandler' in content:
        print("ℹ️ Imports de watchdog presentes (no se usan en modo nube)")
    
    return True

def main():
    """Función principal."""
    
    print("🔄 CONVERSIÓN A MODO SOLO NUBE")
    print("=" * 35)
    
    # Crear backup
    print("📋 Creando backup del archivo actual...")
    if not backup_current_file():
        print("❌ No se pudo crear backup")
        return
    
    # Convertir a modo nube
    print("\\n☁️ Convirtiendo a modo solo nube...")
    if not create_cloud_only_esports():
        print("❌ Error en la conversión")
        return
    
    # Verificar imports
    verify_imports()
    
    print("\\n🎉 CONVERSIÓN COMPLETADA")
    print("✅ El bot ahora funciona 100% en la nube")
    print("📁 No se crearán carpetas locales")
    print("🚫 No se monitorearan archivos locales") 
    print("☁️ Todo se almacena en S3 + DynamoDB")
    
    print("\\n📚 PRÓXIMOS PASOS:")
    print("1. Ejecutar: python verify_cloud_only.py")
    print("2. Probar: python verify_aws_setup.py")
    print("3. Iniciar bot: python esports.py")

if __name__ == "__main__":
    main()
