# Verificación final del modo cloud-only
import os
import json
from dotenv import load_dotenv

def verify_cloud_only_setup():
    """Verifica que el setup cloud-only esté completo y funcional."""
    
    print("🔍 VERIFICACIÓN FINAL - MODO CLOUD-ONLY")
    print("=" * 50)
    
    # Cargar variables de entorno
    load_dotenv()
    
    # 1. Verificar variables de entorno AWS
    print("\n1. 📋 VARIABLES DE ENTORNO AWS:")
    aws_vars = {
        'AWS_ACCESS_KEY_ID': os.getenv('AWS_ACCESS_KEY_ID'),
        'AWS_SECRET_ACCESS_KEY': os.getenv('AWS_SECRET_ACCESS_KEY'),
        'AWS_REGION': os.getenv('AWS_REGION'),
        'S3_BUCKET_NAME': os.getenv('S3_BUCKET_NAME'),
        'DYNAMODB_TABLE_NAME': os.getenv('DYNAMODB_TABLE_NAME')
    }
    
    for var, value in aws_vars.items():
        status = "✅" if value else "❌"
        print(f"   {status} {var}: {'CONFIGURADO' if value else 'NO CONFIGURADO'}")
    
    # 2. Verificar variables de entorno APIs
    print("\n2. 🔑 VARIABLES DE ENTORNO APIs:")
    api_vars = {
        'OPENAI_API_KEY': os.getenv('OPENAI_API_KEY'),
        'DISCORD_TOKEN': os.getenv('DISCORD_TOKEN'),
        'GOOGLE_APPLICATION_CREDENTIALS': os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
    }
    
    for var, value in api_vars.items():
        status = "✅" if value else "❌"
        print(f"   {status} {var}: {'CONFIGURADO' if value else 'NO CONFIGURADO'}")
    
    # 3. Verificar archivos de configuración
    print("\n3. 📁 ARCHIVOS DE CONFIGURACIÓN:")
    config_files = [
        'esports.py',
        'dynamodb_config.py', 
        's3_config.py',
        '.env'
    ]
    
    for file in config_files:
        exists = os.path.exists(file)
        status = "✅" if exists else "❌"
        print(f"   {status} {file}: {'EXISTE' if exists else 'NO EXISTE'}")
    
    # 4. Verificar que esports.py sea la versión cloud-only
    print("\n4. 🔧 VERIFICACIÓN DE CÓDIGO CLOUD-ONLY:")
    try:
        with open('esports.py', 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Verificar características cloud-only
        cloud_features = {
            'Sin watchdog': 'from watchdog' not in content,
            'Procesamiento Discord': 'process_audio_attachment' in content,
            'TTS en memoria': 'generate_tts_audio_to_bytes' in content,
            'AWS S3 + DynamoDB': 'save_analysis_complete' in content,
            'Sin archivos locales': 'recordings/' not in content or content.count('recordings/') < 3
        }
        
        for feature, check in cloud_features.items():
            status = "✅" if check else "❌"
            print(f"   {status} {feature}: {'IMPLEMENTADO' if check else 'NO IMPLEMENTADO'}")
            
    except Exception as e:
        print(f"   ❌ Error leyendo esports.py: {e}")
    
    # 5. Verificar funciones principales
    print("\n5. ⚙️ FUNCIONES PRINCIPALES:")
    try:
        # Importar módulos principales
        import dynamodb_config
        import s3_config
        
        functions = {
            'save_analysis_complete': hasattr(dynamodb_config, 'save_analysis_complete'),
            'S3 config': hasattr(s3_config, 'upload_file_to_s3'),
            'DynamoDB config': hasattr(dynamodb_config, 'dynamodb_manager')
        }
        
        for func, exists in functions.items():
            status = "✅" if exists else "❌"
            print(f"   {status} {func}: {'DISPONIBLE' if exists else 'NO DISPONIBLE'}")
            
    except Exception as e:
        print(f"   ❌ Error importando módulos: {e}")
    
    # 6. Resumen final
    print("\n6. 📊 RESUMEN FINAL:")
    
    all_aws_vars = all(aws_vars.values())
    all_api_vars = all(api_vars.values())
    esports_exists = os.path.exists('esports.py')
    
    overall_status = all_aws_vars and all_api_vars and esports_exists
    
    if overall_status:
        print("   🎉 CONFIGURACIÓN CLOUD-ONLY COMPLETA")
        print("   ✅ El bot está listo para funcionar en modo solo nube")
        print("\n🚀 PARA EJECUTAR:")
        print("   python esports.py")
        print("\n📱 FUNCIONALIDADES:")
        print("   • Subir archivos MP3/WAV al bot de Discord")
        print("   • Transcripción automática con Whisper")
        print("   • Análisis personalizado con GPT-4")
        print("   • Almacenamiento en S3 + DynamoDB")
        print("   • Feedback por audio TTS")
        print("   • Sin archivos locales")
    else:
        print("   ⚠️ CONFIGURACIÓN INCOMPLETA")
        if not all_aws_vars:
            print("   • Faltan variables AWS")
        if not all_api_vars:
            print("   • Faltan APIs")
        if not esports_exists:
            print("   • Falta esports.py")
    
    print("\n" + "=" * 50)
    return overall_status

if __name__ == "__main__":
    verify_cloud_only_setup()
