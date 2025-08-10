import boto3
import os
import sys
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

def create_preferences_table():
    """
    Crea la tabla ClutchPreferences en DynamoDB.
    """
    try:
        # Configuración de DynamoDB
        DYNAMODB_REGION = os.getenv('AWS_REGION')
        
        if not DYNAMODB_REGION:
            sys.stderr.write("❌ AWS_REGION no está configurado en .env\n")
            return False
            
        dynamodb = boto3.resource(
            'dynamodb',
            region_name=DYNAMODB_REGION,
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
        )

        table_name = 'ClutchPreferences'
        
        # Verificar si la tabla ya existe
        try:
            existing_table = dynamodb.Table(table_name)
            existing_table.load()  # Esto lanzará una excepción si la tabla no existe
            print(f"✅ La tabla {table_name} ya existe.")
            
            # Mostrar información de la tabla
            print(f"   - Estado: {existing_table.table_status}")
            print(f"   - Elementos: {existing_table.item_count}")
            print(f"   - Fecha de creación: {existing_table.creation_date_time}")
            return True
            
        except Exception:
            # La tabla no existe, la creamos
            pass

        print(f"🔨 Creando tabla DynamoDB: {table_name}")
        
        # Crear la tabla
        table = dynamodb.create_table(
            TableName=table_name,
            KeySchema=[
                {
                    'AttributeName': 'user_id',
                    'KeyType': 'HASH'  # Partition key
                }
            ],
            AttributeDefinitions=[
                {
                    'AttributeName': 'user_id',
                    'AttributeType': 'S'  # String
                }
            ],
            BillingMode='PAY_PER_REQUEST',  # Facturación bajo demanda
            Tags=[
                {
                    'Key': 'Project',
                    'Value': 'CLUTCH'
                },
                {
                    'Key': 'Purpose',
                    'Value': 'UserPreferences'
                }
            ]
        )

        # Esperar hasta que la tabla esté lista
        print("⏳ Esperando que la tabla esté disponible...")
        table.wait_until_exists()
        
        print(f"✅ Tabla {table_name} creada exitosamente!")
        print(f"   - ARN: {table.table_arn}")
        print(f"   - Estado: {table.table_status}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error creando la tabla: {e}")
        return False

def show_table_info():
    """
    Muestra información sobre la tabla ClutchPreferences.
    """
    try:
        DYNAMODB_REGION = os.getenv('AWS_REGION')
        
        if not DYNAMODB_REGION:
            sys.stderr.write("❌ AWS_REGION no está configurado en .env\n")
            return
            
        dynamodb = boto3.resource(
            'dynamodb',
            region_name=DYNAMODB_REGION,
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
        )

        table = dynamodb.Table('ClutchPreferences')
        table.load()
        
        print("📋 Información de la tabla ClutchPreferences:")
        print(f"   - Estado: {table.table_status}")
        print(f"   - Elementos: {table.item_count}")
        print(f"   - Clave primaria: user_id (String)")
        print(f"   - Modo de facturación: {table.billing_mode_summary}")
        print(f"   - Fecha de creación: {table.creation_date_time}")
        print(f"   - ARN: {table.table_arn}")
        
        # Esquema de la tabla
        print("\n📝 Estructura de elementos:")
        print("   - user_id (String): ID único del usuario Discord")
        print("   - tts_preferences (Map): Configuraciones de TTS")
        print("     - elevenlabs_voice (String): ID de voz de ElevenLabs")
        print("     - tts_speed (String): Velocidad del audio (Lenta/Normal/Rapida)")
        print("   - user_personality_test (List): Respuestas del test TIPI (10 números)")
        print("   - profile_id (String): Perfil calculado (ej: E_alto__A_medio__N_bajo__C_alto__O_medio)")
        print("   - created_at (String): Timestamp de creación")
        print("   - updated_at (String): Timestamp de última actualización")
        
    except Exception as e:
        print(f"❌ Error obteniendo información de la tabla: {e}")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "info":
        show_table_info()
    else:
        create_preferences_table()
