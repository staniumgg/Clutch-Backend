"""
Script para crear automáticamente la tabla de DynamoDB para Clutch.
Ejecutar este script una vez para configurar la infraestructura.
"""

import boto3
import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

def create_clutch_table():
    """
    Crea la tabla ClutchAnalysis en DynamoDB con la configuración optimizada.
    """
    # Configuración
    table_name = os.getenv('DYNAMODB_TABLE_NAME', 'ClutchAnalysis')
    region = os.getenv('AWS_REGION', 'us-east-1')
    access_key = os.getenv('AWS_ACCESS_KEY_ID')
    secret_key = os.getenv('AWS_SECRET_ACCESS_KEY')
    
    # Validar credenciales
    if not access_key or not secret_key:
        print("❌ Error: Credenciales de AWS no configuradas")
        print("🔧 Configura AWS_ACCESS_KEY_ID y AWS_SECRET_ACCESS_KEY en tu archivo .env")
        print("📖 Para obtener credenciales:")
        print("   1. Ve a https://console.aws.amazon.com/iam/")
        print("   2. Crea un usuario con permisos de DynamoDB")
        print("   3. Genera Access Keys")
        return False
    
    if access_key == "TU_ACCESS_KEY_AQUI" or secret_key == "TU_SECRET_KEY_AQUI":
        print("❌ Error: Usando credenciales de ejemplo")
        print("🔧 Reemplaza los valores de ejemplo con tus credenciales reales de AWS")
        return False
    
    try:
        # Cliente de DynamoDB
        dynamodb = boto3.resource(
            'dynamodb',
            region_name=region,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key
        )
        
        print(f"🚀 Creando tabla '{table_name}' en región {region}...")
        
        # Crear tabla
        table = dynamodb.create_table(
            TableName=table_name,
            KeySchema=[
                {
                    'AttributeName': 'id',
                    'KeyType': 'HASH'  # Clave primaria
                }
            ],
            AttributeDefinitions=[
                {
                    'AttributeName': 'id',
                    'AttributeType': 'S'  # String
                },
                {
                    'AttributeName': 'user_id',
                    'AttributeType': 'S'  # String
                },
                {
                    'AttributeName': 'created_date',
                    'AttributeType': 'S'  # String (formato YYYY-MM-DD)
                }
            ],
            # Índices para consultas eficientes
            GlobalSecondaryIndexes=[
                {
                    'IndexName': 'UserIndex',
                    'KeySchema': [
                        {
                            'AttributeName': 'user_id',
                            'KeyType': 'HASH'
                        },
                        {
                            'AttributeName': 'created_date', 
                            'KeyType': 'RANGE'
                        }
                    ],
                    'Projection': {
                        'ProjectionType': 'ALL'
                    }
                    # BillingMode se configura a nivel de tabla, no de índice
                }
            ],
            # Configuración de facturación (Pay-per-request es más económico para proyectos pequeños)
            BillingMode='PAY_PER_REQUEST',
            # Tags para organización
            Tags=[
                {
                    'Key': 'Project',
                    'Value': 'Clutch-eSports-Analysis'
                },
                {
                    'Key': 'Environment',
                    'Value': 'Production'
                }
            ]
        )
        
        # Esperar a que la tabla se cree
        print("⏳ Esperando a que la tabla se active...")
        table.wait_until_exists()
          print(f"✅ ¡Tabla '{table_name}' creada exitosamente!")
        print(f"📊 Detalles de la tabla:")
        print(f"   - Nombre: {table.table_name}")
        print(f"   - Estado: {table.table_status}")
        print(f"   - Región: {region}")
        print(f"   - Billing: Pay-per-request (ideal para proyectos pequeños)")
        
        return True
        
    except Exception as e:
        if "ResourceInUseException" in str(e):
            print(f"⚠️ La tabla '{table_name}' ya existe.")
            return True
        elif "UnauthorizedOperation" in str(e) or "AccessDenied" in str(e):
            print(f"❌ Error de permisos: {e}")
            print("🔧 Soluciones:")
            print("   1. Verificar que las credenciales de AWS sean correctas")
            print("   2. Asegurar que el usuario tenga permisos de DynamoDB")
            print("   3. Verificar que la región sea correcta")
        elif "NoRegionError" in str(e):
            print(f"❌ Error de región: {e}")
            print("🔧 Configura AWS_REGION en tu archivo .env")
        else:
            print(f"❌ Error creando la tabla: {e}")
            print("🔧 Soluciones posibles:")
            print("   1. Verificar credenciales de AWS")
            print("   2. Verificar permisos de DynamoDB") 
            print("   3. Verificar región correcta")
        return False

def verify_table_setup():
    """
    Verifica que la tabla esté configurada correctamente.
    """
    table_name = os.getenv('DYNAMODB_TABLE_NAME', 'ClutchAnalysis')
    region = os.getenv('AWS_REGION', 'us-east-1')
    
    dynamodb = boto3.resource(
        'dynamodb',
        region_name=region,
        aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
    )
    
    try:
        table = dynamodb.Table(table_name)
        response = table.describe()
        
        print(f"\n📋 Información de la tabla '{table_name}':")
        print(f"   - Estado: {response['Table']['TableStatus']}")
        print(f"   - Elementos: {response['Table']['ItemCount']}")
        print(f"   - Tamaño: {response['Table']['TableSizeBytes']} bytes")
        print(f"   - Índices: {len(response['Table'].get('GlobalSecondaryIndexes', []))}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error verificando tabla: {e}")
        return False

def estimate_costs():
    """
    Proporciona estimación de costos para DynamoDB.
    """
    print(f"\n💰 Estimación de costos de DynamoDB:")
    print(f"   📊 Tier gratuito (primeros 12 meses):")
    print(f"      - 25 GB de almacenamiento: GRATIS")
    print(f"      - 25 WCU y 25 RCU: GRATIS")
    print(f"      - 200 millones de requests: GRATIS")
    print(f"   ")
    print(f"   💸 Después del tier gratuito (Pay-per-request):")
    print(f"      - Escritura: $1.25 por millón de requests")
    print(f"      - Lectura: $0.25 por millón de requests") 
    print(f"      - Almacenamiento: $0.25 per GB/mes")
    print(f"   ")
    print(f"   🎮 Para tu proyecto Clutch:")
    print(f"      - ~100 análisis/día = ~3000/mes")
    print(f"      - Costo estimado: <$1 USD/mes después del tier gratuito")

if __name__ == "__main__":
    print("🏗️ Configurador de DynamoDB para Clutch")
    print("=" * 50)
      # Verificar variables de entorno
    required_vars = ['AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY', 'AWS_REGION']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"❌ Variables de entorno faltantes: {missing_vars}")
        print("🔧 Configura estas variables en tu archivo .env:")
        print("   AWS_ACCESS_KEY_ID=tu_access_key_real")
        print("   AWS_SECRET_ACCESS_KEY=tu_secret_key_real") 
        print("   AWS_REGION=us-east-1")
        print("\n📖 Para obtener credenciales de AWS:")
        print("   1. Ve a https://console.aws.amazon.com/iam/")
        print("   2. Crea un usuario con permisos de DynamoDB")
        print("   3. Genera Access Keys")
        exit(1)
    
    # Crear tabla
    if create_clutch_table():
        verify_table_setup()
        estimate_costs()
        print(f"\n🎉 ¡Configuración completada! Ya puedes usar DynamoDB en Clutch.")
    else:
        print(f"\n❌ Configuración falló. Revisa los errores anteriores.")
