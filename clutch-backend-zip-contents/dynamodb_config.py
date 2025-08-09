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
    player_audio_data: bytes,
    coach_audio_data: bytes,
    base_filename: str,
    transcription: str,
    user_preferences: Dict,
    wpm: float = 0.0,
    wmp_by_segment: dict = None # Añadir wmp por segmento
) -> Dict:
    """
    Orquesta el proceso completo: sube audio del jugador y del coach a S3 y guarda el análisis en DynamoDB.
    """
    result = {
        'success': False,
        'analysis_id': "local-" + str(uuid.uuid4()),
        'player_s3_url': '',
        'coach_s3_url': '',
        'error': ''
    }

    # 1. Subir audio del jugador a S3
    player_s3_url = ""
    coach_s3_url = ""
    analysis_id = str(uuid.uuid4())
    player_filename = f"player_{analysis_id}.mp3"
    coach_filename = f"coach_{analysis_id}.mp3"
    if S3_AVAILABLE and s3_manager and player_audio_data:
        try:
            player_s3_url = s3_manager.upload_audio_from_bytes(player_audio_data, user_id, player_filename)
            if player_s3_url:
                result['player_s3_url'] = player_s3_url
                sys.stderr.write(f"✅ Audio del jugador subido a S3: {player_s3_url}\n")
            else:
                sys.stderr.write("⚠️  No se pudo subir audio del jugador a S3.\n")
        except Exception as e:
            sys.stderr.write(f"⚠️  Error subiendo audio del jugador a S3: {e}\n")
    elif not S3_AVAILABLE:
        sys.stderr.write("ℹ️ S3 no está disponible, omitiendo subida de audio del jugador.\n")
    elif not player_audio_data:
        sys.stderr.write(f"⚠️  No hay datos de audio del jugador, no se puede subir a S3.\n")

    # 2. Subir audio del coach a S3
    if S3_AVAILABLE and s3_manager and coach_audio_data:
        try:
            coach_s3_url = s3_manager.upload_audio_from_bytes(coach_audio_data, user_id, coach_filename)
            if coach_s3_url:
                result['coach_s3_url'] = coach_s3_url
                sys.stderr.write(f"✅ Audio del coach subido a S3: {coach_s3_url}\n")
            else:
                sys.stderr.write("⚠️  No se pudo subir audio del coach a S3.\n")
        except Exception as e:
            sys.stderr.write(f"⚠️  Error subiendo audio del coach a S3: {e}\n")
    elif not S3_AVAILABLE:
        sys.stderr.write("ℹ️ S3 no está disponible, omitiendo subida de audio del coach.\n")
    elif not coach_audio_data:
        sys.stderr.write(f"⚠️  No hay datos de audio del coach, no se puede subir a S3.\n")

    # 3. Guardar análisis en DynamoDB
    if not DYNAMODB_AVAILABLE:
        result['error'] = 'DynamoDB no está disponible.'
        sys.stderr.write("⚠️  DynamoDB no disponible, análisis no guardado en la nube.\n")
        return result

    try:
        table = dynamodb.Table(DYNAMODB_TABLE_NAME)
        item = {
            'id': analysis_id,  # DynamoDB requiere este campo como clave primaria
            'analysis_id': analysis_id,
            'user_id': user_id,
            'player_audio_url': player_s3_url,  # URL del audio del jugador
            'coach_audio_url': coach_s3_url,    # URL del audio del coach
            'analysis_text': analysis_text,
            'transcription': transcription,
            'user_preferences': user_preferences,
            'timestamp': datetime.utcnow().isoformat(),
            'game': user_preferences.get('game', 'N/A'),
            'coach_type': user_preferences.get('coach_type', 'N/A'),
            'wmp': int(wpm),  # Guardar WMP como entero
            'wmp_by_segment': wmp_by_segment if wmp_by_segment else {}
        }
        table.put_item(Item=item)
        result['success'] = True
        result['analysis_id'] = analysis_id
        sys.stderr.write(f"✅ Análisis guardado en DynamoDB. ID: {analysis_id}\n")
    except Exception as e:
        result['error'] = f"Error al guardar en DynamoDB: {e}"
        sys.stderr.write(f"❌ Error guardando análisis en DynamoDB: {e}\n")
    return result

def get_analyses_by_user(user_id: str) -> Dict:
    """
    Obtiene todos los análisis de un usuario desde DynamoDB.
    """
    if not DYNAMODB_AVAILABLE:
        return {'success': False, 'error': 'DynamoDB no está disponible.'}

    try:
        table = dynamodb.Table(DYNAMODB_TABLE_NAME)
        response = table.query(
            IndexName='user_id-index',  # Asumiendo que tienes un GSI en 'user_id'
            KeyConditionExpression=boto3.dynamodb.conditions.Key('user_id').eq(user_id)
        )
        return {'success': True, 'data': response.get('Items', [])}
    except Exception as e:
        error_message = f"Error al obtener análisis de DynamoDB: {e}"
        sys.stderr.write(f"❌ {error_message}\n")
        return {'success': False, 'error': error_message}
