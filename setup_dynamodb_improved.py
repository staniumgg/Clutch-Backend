"""
Script para configurar DynamoDB para el proyecto Clutch.
Soporta tanto AWS real como DynamoDB Local.
"""

import boto3
import os
from dotenv import load_dotenv
from botocore.exceptions import ClientError, NoCredentialsError
import sys

# Cargar variables de entorno
load_dotenv()

def check_aws_credentials():
    """Verifica si las credenciales de AWS son válidas."""
    access_key = os.getenv('AWS_ACCESS_KEY_ID')
    secret_key = os.getenv('AWS_SECRET_ACCESS_KEY')
    
    print("🔍 Verificando credenciales AWS...")
    print(f"AWS_ACCESS_KEY_ID: {access_key[:10]}..." if access_key else "No configurado")
    print(f"AWS_SECRET_ACCESS_KEY: {'*' * 20}" if secret_key else "No configurado")
    
    # Validar formato de credenciales
    if access_key and len(access_key) == 20 and access_key.startswith('AKIA'):
        if secret_key and len(secret_key) == 40:
            return True, "Credenciales con formato válido"
        else:
            return False, "SECRET_ACCESS_KEY debe tener 40 caracteres"
    else:
        return False, "ACCESS_KEY_ID debe tener 20 caracteres y empezar con 'AKIA'"

def setup_dynamodb_table():
    """Configura la tabla de DynamoDB."""
    region = os.getenv('AWS_REGION', 'us-east-1')
    table_name = os.getenv('DYNAMODB_TABLE_NAME', 'ClutchAnalysis')
    endpoint_url = os.getenv('DYNAMODB_ENDPOINT')
    
    # Configuración de DynamoDB
    dynamodb_config = {
        'region_name': region,
        'aws_access_key_id': os.getenv('AWS_ACCESS_KEY_ID'),
        'aws_secret_access_key': os.getenv('AWS_SECRET_ACCESS_KEY')
    }
    
    if endpoint_url:
        dynamodb_config['endpoint_url'] = endpoint_url
        print(f"🔧 Usando DynamoDB Local: {endpoint_url}")
    else:
        print(f"☁️ Usando AWS DynamoDB en región: {region}")
    
    try:
        # Crear cliente de DynamoDB
        dynamodb = boto3.resource('dynamodb', **dynamodb_config)
        
        # Verificar si la tabla ya existe
        try:
            table = dynamodb.Table(table_name)
            table.load()
            print(f"✅ Tabla '{table_name}' ya existe")
            
            # Mostrar información de la tabla
            print(f"📊 Estado: {table.table_status}")
            print(f"📊 Elementos: {table.item_count}")
            return True
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                print(f"📋 Creando tabla '{table_name}'...")
                
                # Crear la tabla
                table = dynamodb.create_table(
                    TableName=table_name,
                    KeySchema=[
                        {
                            'AttributeName': 'id',
                            'KeyType': 'HASH'  # Partition key
                        }
                    ],
                    AttributeDefinitions=[
                        {
                            'AttributeName': 'id',
                            'AttributeType': 'S'
                        },
                        {
                            'AttributeName': 'user_id',
                            'AttributeType': 'S'
                        }
                    ],                    GlobalSecondaryIndexes=[
                        {
                            'IndexName': 'UserIndex',
                            'KeySchema': [
                                {
                                    'AttributeName': 'user_id',
                                    'KeyType': 'HASH'
                                }
                            ],
                            'Projection': {
                                'ProjectionType': 'ALL'
                            }
                        }
                    ],
                    BillingMode='PAY_PER_REQUEST'
                )
                
                # Esperar a que la tabla esté activa
                print("⏳ Esperando que la tabla esté activa...")
                table.wait_until_exists()
                print(f"✅ Tabla '{table_name}' creada exitosamente")
                return True
            else:
                raise e
                
    except NoCredentialsError:
        print("❌ Error: No se encontraron credenciales AWS")
        print("💡 Configura AWS_ACCESS_KEY_ID y AWS_SECRET_ACCESS_KEY en el archivo .env")
        return False
    except Exception as e:
        print(f"❌ Error configurando DynamoDB: {e}")
        return False

def test_dynamodb_connection():
    """Prueba la conexión a DynamoDB."""
    try:
        from dynamodb_config import dynamodb_manager
        
        # Intentar guardar un análisis de prueba
        print("🧪 Probando conexión con DynamoDB...")
        
        test_analysis_id = dynamodb_manager.save_analysis(
            user_id="test_user_123",
            analysis_text="Análisis de prueba para verificar la conexión a DynamoDB",
            transcription="Transcripción de prueba",
            user_preferences={"test": True}
        )
        
        if test_analysis_id.startswith("local-") or test_analysis_id.startswith("error-"):
            print("⚠️ Guardado en modo local (DynamoDB no disponible)")
            return False
        else:
            print(f"✅ Conexión exitosa - ID de prueba: {test_analysis_id}")
            
            # Intentar obtener estadísticas
            stats = dynamodb_manager.get_user_stats("test_user_123")
            print(f"📊 Estadísticas de prueba: {stats}")
            return True
            
    except Exception as e:
        print(f"❌ Error en prueba de conexión: {e}")
        return False

def main():
    """Función principal del script."""
    print("🚀 Configuración de DynamoDB para Clutch eSports")
    print("=" * 50)
    
    # Verificar credenciales
    creds_valid, creds_msg = check_aws_credentials()
    print(f"🔐 {creds_msg}")
    
    if not creds_valid:
        print("\n💡 Opciones disponibles:")
        print("1. Configurar credenciales AWS reales (ver AWS_SETUP_GUIDE.md)")
        print("2. Usar DynamoDB Local para desarrollo")
        print("3. Continuar sin DynamoDB (modo local)")
        
        choice = input("\n¿Qué opción prefieres? (1/2/3): ").strip()
        
        if choice == "1":
            print("\n📖 Consulta AWS_SETUP_GUIDE.md para obtener credenciales reales")
            return
        elif choice == "2":
            print("\n🔧 Para usar DynamoDB Local:")
            print("1. Descarga: https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/DynamoDBLocal.html")
            print("2. Ejecuta: java -Djava.library.path=./DynamoDBLocal_lib -jar DynamoDBLocal.jar -sharedDb")
            print("3. Agrega a .env: DYNAMODB_ENDPOINT=http://localhost:8000")
            return
        else:
            print("\n⚠️ Continuando sin DynamoDB - datos no se persistirán")
    
    # Configurar tabla
    if setup_dynamodb_table():
        print("\n🧪 Ejecutando pruebas de conexión...")
        if test_dynamodb_connection():
            print("\n🎉 ¡Configuración completada exitosamente!")
            print("✅ DynamoDB está listo para usar con Clutch")
        else:
            print("\n⚠️ Configuración completada con advertencias")
    else:
        print("\n❌ Error en la configuración")
        sys.exit(1)

if __name__ == "__main__":
    main()
