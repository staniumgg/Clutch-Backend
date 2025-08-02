"""
Script de verificación final: Configuración completa de AWS para Clutch eSports
Verifica que DynamoDB y S3 estén funcionando correctamente en us-east-2
"""

import os
from datetime import datetime
from dynamodb_config import dynamodb_manager, s3_manager, save_analysis_complete

def check_aws_configuration():
    """Verifica la configuración de AWS."""
    
    print("🔧 VERIFICACIÓN DE CONFIGURACIÓN AWS")
    print("=" * 45)
    
    # Variables de entorno
    region = os.getenv('AWS_REGION')
    access_key = os.getenv('AWS_ACCESS_KEY_ID')
    secret_key = os.getenv('AWS_SECRET_ACCESS_KEY')
    dynamodb_table = os.getenv('DYNAMODB_TABLE_NAME')
    s3_bucket = os.getenv('S3_BUCKET_NAME')
    
    print(f"🌍 Región AWS: {region}")
    print(f"🔑 Access Key: {access_key[:10]}..." if access_key else "❌ No configurado")
    print(f"🔐 Secret Key: {'*' * 20}" if secret_key else "❌ No configurado")
    print(f"💾 Tabla DynamoDB: {dynamodb_table}")
    print(f"🪣 Bucket S3: {s3_bucket}")
    
    return all([region, access_key, secret_key, dynamodb_table, s3_bucket])

def check_dynamodb_connection():
    """Verifica la conexión a DynamoDB."""
    
    print("\n💾 VERIFICACIÓN DE DYNAMODB")
    print("=" * 35)
    
    try:
        # Probar guardado simple
        test_user = "test_verification_123"
        test_analysis = f"Análisis de verificación - {datetime.now().isoformat()}"
        
        analysis_id = dynamodb_manager.save_analysis(
            user_id=test_user,
            analysis_text=test_analysis,
            transcription="Test transcription",
            user_preferences={"test": True}
        )
        
        if analysis_id and not analysis_id.startswith("error-"):
            print("✅ DynamoDB: Conexión exitosa")
            print(f"✅ Análisis de prueba guardado: {analysis_id}")
            
            # Obtener estadísticas
            stats = dynamodb_manager.get_user_stats(test_user)
            print(f"📊 Estadísticas obtenidas: {stats}")
            
            return True
        else:
            print("❌ DynamoDB: Error en guardado")
            return False
            
    except Exception as e:
        print(f"❌ DynamoDB: Error de conexión - {e}")
        return False

def check_s3_connection():
    """Verifica la conexión a S3."""
    
    print("\n🪣 VERIFICACIÓN DE S3")
    print("=" * 25)
    
    try:
        # Obtener información del bucket
        bucket_info = s3_manager.get_bucket_info()
        
        if 'error' in bucket_info:
            print(f"❌ S3: Error - {bucket_info['error']}")
            return False
        
        print("✅ S3: Conexión exitosa")
        print(f"📁 Bucket: {bucket_info['bucket_name']}")
        print(f"🌍 Región: {bucket_info['region']}")
        print(f"📊 Objetos: {bucket_info['total_objects']}")
        print(f"💾 Tamaño: {bucket_info['total_size_mb']} MB")
        
        return True
        
    except Exception as e:
        print(f"❌ S3: Error de conexión - {e}")
        return False

def check_integration():
    """Verifica la integración completa."""
    
    print("\n🔗 VERIFICACIÓN DE INTEGRACIÓN COMPLETA")
    print("=" * 45)
    
    try:
        # Crear archivo temporal de prueba
        test_file = "temp_verification_test.txt"
        test_content = f"Archivo de verificación - {datetime.now().isoformat()}"
        
        with open(test_file, 'w') as f:
            f.write(test_content)
        
        # Probar función integrada
        result = save_analysis_complete(
            user_id="verification_integration_456",
            analysis_text="Análisis de verificación de integración completa",
            audio_file_path=test_file,
            transcription="Test integration transcription",
            user_preferences={"integration_test": True, "timestamp": datetime.now().isoformat()}
        )
        
        # Limpiar archivo temporal
        if os.path.exists(test_file):
            os.remove(test_file)
        
        if result['success']:
            print("✅ Integración: Funcionando correctamente")
            print(f"✅ Analysis ID: {result['analysis_id']}")
            if result['s3_key']:
                print(f"✅ S3 Key: {result['s3_key']}")
            return True
        else:
            print(f"❌ Integración: Falló - {result['errors']}")
            return False
            
    except Exception as e:
        print(f"❌ Integración: Error - {e}")
        return False

def show_usage_examples():
    """Muestra ejemplos de uso."""
    
    print("\n📚 EJEMPLOS DE USO EN EL BOT")
    print("=" * 35)
    
    print("""
1. 📤 Subir audio y guardar análisis (Función completa):
   
   result = save_analysis_complete(
       user_id="1106372321582784603",
       analysis_text="Análisis generado por GPT...",
       audio_file_path="recordings/audio.mp3",
       transcription="Transcripción de Whisper...",
       user_preferences={"coach_type": "Motivacional"}
   )

2. 📊 Consultar análisis del usuario:
   
   analyses = dynamodb_manager.get_user_analyses("1106372321582784603")
   latest_analysis = analyses[0] if analyses else None

3. 📈 Obtener estadísticas del usuario:
   
   stats = dynamodb_manager.get_user_stats("1106372321582784603")
   total_analyses = stats.get('total_analyses', 0)

4. 🎵 Obtener archivos de audio del usuario:
   
   user_audios = s3_manager.get_user_audios("1106372321582784603")
   for audio in user_audios:
       print(f"Audio: {audio['s3_key']}")
""")

def main():
    """Función principal de verificación."""
    
    print("🎮 CLUTCH ESPORTS - VERIFICACIÓN FINAL DE AWS")
    print("📅 Configuración para región us-east-2 (Ohio)")
    print("🔧 Integración S3 + DynamoDB")
    print("=" * 60)
    
    # Verificaciones
    config_ok = check_aws_configuration()
    dynamodb_ok = check_dynamodb_connection()
    s3_ok = check_s3_connection()
    integration_ok = check_integration()
    
    # Resumen
    print("\n📊 RESUMEN DE VERIFICACIÓN")
    print("=" * 30)
    print(f"🔧 Configuración AWS: {'✅' if config_ok else '❌'}")
    print(f"💾 DynamoDB: {'✅' if dynamodb_ok else '❌'}")
    print(f"🪣 S3: {'✅' if s3_ok else '❌'}")
    print(f"🔗 Integración: {'✅' if integration_ok else '❌'}")
    
    if all([config_ok, dynamodb_ok, s3_ok, integration_ok]):
        print(f"\n🎉 ¡CONFIGURACIÓN COMPLETA Y FUNCIONAL!")
        print(f"✅ El bot está listo para:")
        print(f"   📤 Subir archivos de audio a S3")
        print(f"   💾 Guardar análisis en DynamoDB")
        print(f"   📊 Consultar historial y estadísticas")
        print(f"   🔗 Integración completa funcionando")
        
        show_usage_examples()
        
        print(f"\n💡 PRÓXIMOS PASOS:")
        print(f"   1. El bot ya está configurado para usar AWS")
        print(f"   2. Los audios se subirán automáticamente a S3")
        print(f"   3. Los análisis se guardarán en DynamoDB")
        print(f"   4. Puedes consultar el historial usando el dashboard")
        
    else:
        print(f"\n⚠️ Hay problemas en la configuración")
        print(f"❗ Revisa los errores mostrados arriba")
        
        if not config_ok:
            print(f"🔧 Configura las variables de entorno en .env")
        if not dynamodb_ok:
            print(f"💾 Verifica la tabla DynamoDB y credenciales")
        if not s3_ok:
            print(f"🪣 Verifica el bucket S3 y permisos")

if __name__ == "__main__":
    main()
