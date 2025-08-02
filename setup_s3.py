"""
Script para configurar Amazon S3 para almacenar archivos de audio.
Crea el bucket necesario y configura las políticas básicas.
"""

import boto3
import os
from dotenv import load_dotenv
from botocore.exceptions import ClientError

# Cargar variables de entorno
load_dotenv()

def create_s3_bucket():
    """Crea el bucket de S3 para almacenar audios."""
    
    # Configuración
    bucket_name = os.getenv('S3_BUCKET_NAME', 'clutch-esports-audio-ohio')
    region = os.getenv('AWS_REGION', 'us-east-2')
    
    print(f"🪣 Configurando bucket S3: {bucket_name}")
    print(f"🌍 Región: {region} (Ohio - mejor para Latinoamérica)")
    
    try:
        # Crear cliente S3
        s3_client = boto3.client(
            's3',
            region_name=region,
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
        )
        
        # Verificar si el bucket ya existe
        try:
            s3_client.head_bucket(Bucket=bucket_name)
            print(f"✅ Bucket '{bucket_name}' ya existe")
            return True
            
        except ClientError as e:
            error_code = int(e.response['Error']['Code'])
            if error_code == 404:                # Crear bucket
                print(f"📋 Creando bucket '{bucket_name}' en {region}...")
                
                # Para us-east-2 necesitamos especificar LocationConstraint
                s3_client.create_bucket(
                    Bucket=bucket_name,
                    CreateBucketConfiguration={'LocationConstraint': region}
                )
                
                print(f"✅ Bucket '{bucket_name}' creado exitosamente")
                
                # Configurar versionado (opcional pero recomendado)
                try:
                    s3_client.put_bucket_versioning(
                        Bucket=bucket_name,
                        VersioningConfiguration={'Status': 'Enabled'}
                    )
                    print("✅ Versionado habilitado")
                except Exception as ve:
                    print(f"⚠️ No se pudo habilitar versionado: {ve}")
                
                # Configurar políticas de lifecycle (eliminar archivos antiguos)
                try:
                    lifecycle_config = {
                        'Rules': [
                            {
                                'ID': 'DeleteOldAudios',
                                'Status': 'Enabled',
                                'Filter': {'Prefix': 'audios/'},
                                'Expiration': {'Days': 90}  # Eliminar después de 90 días
                            }
                        ]
                    }
                    
                    s3_client.put_bucket_lifecycle_configuration(
                        Bucket=bucket_name,
                        LifecycleConfiguration=lifecycle_config
                    )
                    print("✅ Políticas de lifecycle configuradas (eliminar después de 90 días)")
                except Exception as le:
                    print(f"⚠️ No se pudieron configurar políticas de lifecycle: {le}")
                
                return True
            else:
                print(f"❌ Error verificando bucket: {e}")
                return False
                
    except Exception as e:
        print(f"❌ Error configurando S3: {e}")
        return False

def test_s3_upload():
    """Prueba la subida de un archivo de prueba a S3."""
    
    print("\n🧪 Probando subida a S3...")
    
    try:
        from s3_config import s3_manager
        
        # Crear archivo de prueba temporal
        test_content = "Este es un archivo de prueba para verificar la conexión con S3"
        test_file = "temp_test_file.txt"
        
        with open(test_file, 'w') as f:
            f.write(test_content)
        
        # Subir archivo de prueba
        s3_key = s3_manager.upload_audio(test_file, "test_user_123")
        
        if s3_key:
            print(f"✅ Archivo de prueba subido: {s3_key}")
            
            # Generar URL firmada
            url = s3_manager.get_presigned_url(s3_key, 300)  # 5 minutos
            if url:
                print(f"✅ URL firmada generada: {url[:60]}...")
            
            # Limpiar archivo de prueba
            s3_manager.delete_audio(s3_key)
            print("✅ Archivo de prueba eliminado")
            
        # Limpiar archivo local
        if os.path.exists(test_file):
            os.remove(test_file)
        
        return True
        
    except Exception as e:
        print(f"❌ Error en prueba de S3: {e}")
        return False

def show_cost_estimate():
    """Muestra estimación de costos de S3."""
    
    print("\n💰 ESTIMACIÓN DE COSTOS S3:")
    print("=" * 40)
    print("📊 Precios aproximados en us-east-2 (Ohio):")
    print("   • Almacenamiento: $0.023 por GB/mes")
    print("   • Requests PUT: $0.0005 por 1,000 requests")
    print("   • Requests GET: $0.0004 por 1,000 requests")
    print("   • Transferencia salida: $0.09 por GB")
    print("   • 🌎 Mejor latencia para Latinoamérica")
    print()
    print("📈 Para tu proyecto (estimado):")
    print("   • 100 audios/mes × 1MB c/u = 100MB")
    print("   • Costo mensual estimado: ~$0.02-0.05 USD")
    print("   • Primer año prácticamente GRATIS")
    print()
    print("🆓 Tier gratuito de AWS S3:")
    print("   • 5 GB de almacenamiento")
    print("   • 20,000 GET requests")
    print("   • 2,000 PUT requests")

def main():
    """Función principal del script."""
    
    print("🚀 Configuración de Amazon S3 para Clutch eSports")
    print("=" * 55)
    
    # Mostrar estimación de costos
    show_cost_estimate()
      # Confirmar configuración
    bucket_name = os.getenv('S3_BUCKET_NAME', 'clutch-esports-audio-ohio')
    
    print(f"\n🔧 Configuración actual:")
    print(f"   • Bucket: {bucket_name}")
    print(f"   • Región: {os.getenv('AWS_REGION', 'us-east-2')} (Ohio)")
    
    proceed = input(f"\n¿Continuar con la configuración? (y/n): ").lower().strip()
    
    if proceed != 'y':
        print("❌ Configuración cancelada")
        return
    
    # Crear bucket
    if create_s3_bucket():
        print(f"\n🧪 Ejecutando pruebas...")
        if test_s3_upload():
            print(f"\n🎉 ¡S3 configurado exitosamente!")
            print(f"✅ Ya puedes subir archivos de audio a: {bucket_name}")
            print(f"💡 Archivos se eliminarán automáticamente después de 90 días")
        else:
            print(f"\n⚠️ S3 configurado pero las pruebas fallaron")
    else:
        print(f"\n❌ Error en la configuración de S3")

if __name__ == "__main__":
    main()
