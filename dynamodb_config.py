import boto3
import uuid
from datetime import datetime
import os
import sys
from typing import Dict
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Intentar importar S3 manager
try:
    from s3_config import s3_manager
    S3_AVAILABLE = s3_manager.available
except ImportError:
    S3_AVAILABLE = False
    s3_manager = None

# Configuración de DynamoDB
DYNAMODB_REGION = os.getenv('AWS_REGION')
DYNAMODB_TABLE_NAME = os.getenv('DYNAMODB_TABLE_NAME')

dynamodb = None
DYNAMODB_AVAILABLE = False

if DYNAMODB_REGION and DYNAMODB_TABLE_NAME:
    try:
        dynamodb = boto3.resource(
            'dynamodb',
            region_name=DYNAMODB_REGION,
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
        )
        table = dynamodb.Table(DYNAMODB_TABLE_NAME)
        table.load() # Verifica que la tabla existe y se puede acceder
        DYNAMODB_AVAILABLE = True
        sys.stderr.write(f"✅ Conectado a DynamoDB en región: {DYNAMODB_REGION}\n")
    except Exception as e:
        sys.stderr.write(f"❌ Error conectando a DynamoDB: {e}\n")
        dynamodb = None
else:
    sys.stderr.write("⚠️  DynamoDB no configurado. AWS_REGION y DYNAMODB_TABLE_NAME son necesarios.\n")


def save_analysis_complete(
    user_id: str,
    analysis_text: str,
    audio_data: bytes,
    base_filename: str,
    transcription: str,
    user_preferences: Dict
) -> Dict:
    """
    Orquesta el proceso completo: sube audio a S3 y guarda el análisis en DynamoDB.
    """
    result = {
        'success': False,
        'analysis_id': "local-" + str(uuid.uuid4()),
        's3_url': '',
        'error': ''
    }

    # 1. Subir audio a S3
    s3_url = ""
    if S3_AVAILABLE and s3_manager and audio_data:
        try:
            s3_url = s3_manager.upload_audio_from_bytes(audio_data, user_id, base_filename)
            if s3_url:
                result['s3_url'] = s3_url
            else:
                sys.stderr.write("⚠️  No se pudo subir audio a S3, se guardará sin URL de audio.\n")
        except Exception as e:
            sys.stderr.write(f"⚠️  Error subiendo a S3 (continuando): {e}\n")
    elif not S3_AVAILABLE:
        sys.stderr.write("ℹ️ S3 no está disponible, omitiendo subida de audio.\n")
    elif not audio_data:
        sys.stderr.write(f"⚠️  No hay datos de audio, no se puede subir a S3.\n")
    # 2. Guardar análisis en DynamoDB
    if not DYNAMODB_AVAILABLE:
        result['error'] = 'DynamoDB no está disponible.'
        sys.stderr.write("⚠️  DynamoDB no disponible, análisis no guardado en la nube.\n")
        return result

    try:
        table = dynamodb.Table(DYNAMODB_TABLE_NAME)
        analysis_id = str(uuid.uuid4())
        
        item = {
            'id': analysis_id,  # DynamoDB requiere este campo como clave primaria
            'analysis_id': analysis_id,
            'user_id': user_id,
            'audio_url': s3_url,
            'analysis_text': analysis_text,
            'transcription': transcription,
            'user_preferences': user_preferences,
            'timestamp': datetime.utcnow().isoformat(),
            'game': user_preferences.get('game', 'N/A'),
            'coach_type': user_preferences.get('coach_type', 'N/A')
        }
        
        table.put_item(Item=item)
        
        result['success'] = True
        result['analysis_id'] = analysis_id
        sys.stderr.write(f"✅ Análisis guardado en DynamoDB. ID: {analysis_id}\n")
        
    except Exception as e:
        result['error'] = f"Error al guardar en DynamoDB: {e}"
        sys.stderr.write(f"❌ Error guardando análisis en DynamoDB: {e}\n")

    return result
