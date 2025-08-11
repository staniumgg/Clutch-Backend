import boto3
import json
from datetime import datetime
import os
import sys
from typing import Dict, Optional
from dotenv import load_dotenv
from decimal import Decimal

# Cargar variables de entorno
load_dotenv()

# Configuración de DynamoDB
DYNAMODB_REGION = os.getenv('AWS_REGION')
PREFERENCES_TABLE_NAME = "ClutchPreferences"

dynamodb = None
DYNAMODB_AVAILABLE = False

if DYNAMODB_REGION:
    try:
        dynamodb = boto3.resource(
            'dynamodb',
            region_name=DYNAMODB_REGION,
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
        )
        table = dynamodb.Table(PREFERENCES_TABLE_NAME)
        table.load()  # Verifica que la tabla existe y se puede acceder
        DYNAMODB_AVAILABLE = True
        sys.stderr.write(f"✅ Conectado a DynamoDB tabla de preferencias: {PREFERENCES_TABLE_NAME}\n")
    except Exception as e:
        sys.stderr.write(f"❌ Error conectando a DynamoDB tabla de preferencias: {e}\n")
        dynamodb = None
else:
    sys.stderr.write("⚠️  DynamoDB no configurado para preferencias.\n")


def save_user_preferences(user_id: str, tts_preferences: dict, user_personality_test: list, profile_id: str = None) -> Dict:
    """
    Guarda las preferencias del usuario en DynamoDB.
    """
    if not DYNAMODB_AVAILABLE:
        return {'success': False, 'error': 'DynamoDB no está disponible.'}

    try:
        table = dynamodb.Table(PREFERENCES_TABLE_NAME)
        timestamp = datetime.utcnow().isoformat()
        
        item = {
            'user_id': user_id,  # Clave primaria
            'tts_preferences': tts_preferences,
            'user_personality_test': user_personality_test,
            'profile_id': profile_id,
            'created_at': timestamp,
            'updated_at': timestamp
        }
        
        table.put_item(Item=item)
        sys.stderr.write(f"✅ Preferencias guardadas para usuario: {user_id}\n")
        return {'success': True, 'message': 'Preferencias guardadas correctamente'}
        
    except Exception as e:
        error_message = f"Error al guardar preferencias: {e}"
        sys.stderr.write(f"❌ {error_message}\n")
        return {'success': False, 'error': error_message}


def get_user_preferences(user_id: str) -> Dict:
    """
    Obtiene las preferencias del usuario desde DynamoDB.
    """
    if not DYNAMODB_AVAILABLE:
        return {'success': False, 'error': 'DynamoDB no está disponible.'}

    try:
        table = dynamodb.Table(PREFERENCES_TABLE_NAME)
        response = table.get_item(Key={'user_id': user_id})
        
        if 'Item' in response:
            item = response['Item']
            sys.stderr.write(f"✅ Preferencias encontradas para usuario: {user_id}\n")
            
            # Convertir Decimal a int para user_personality_test
            personality_test = item.get('user_personality_test', [])
            if personality_test:
                personality_test = [int(x) if isinstance(x, Decimal) else x for x in personality_test]
            
            return {
                'success': True,
                'preferences': {
                    'tts_preferences': item.get('tts_preferences', {}),
                    'user_personality_test': personality_test,
                    'profile_id': item.get('profile_id', ''),
                    'updated_at': item.get('updated_at', '')
                }
            }
        else:
            sys.stderr.write(f"ℹ️ No se encontraron preferencias para usuario: {user_id}\n")
            return {'success': False, 'error': 'Usuario no encontrado'}
            
    except Exception as e:
        error_message = f"Error al obtener preferencias: {e}"
        sys.stderr.write(f"❌ {error_message}\n")
        return {'success': False, 'error': error_message}


def update_user_preferences(user_id: str, tts_preferences: dict = None, user_personality_test: list = None, profile_id: str = None) -> Dict:
    """
    Actualiza las preferencias del usuario en DynamoDB.
    """
    if not DYNAMODB_AVAILABLE:
        return {'success': False, 'error': 'DynamoDB no está disponible.'}

    try:
        table = dynamodb.Table(PREFERENCES_TABLE_NAME)
        timestamp = datetime.utcnow().isoformat()
        
        # Construir expresión de actualización dinámicamente
        update_expression = "SET updated_at = :timestamp"
        expression_values = {':timestamp': timestamp}
        
        if tts_preferences is not None:
            update_expression += ", tts_preferences = :tts_prefs"
            expression_values[':tts_prefs'] = tts_preferences
            
        if user_personality_test is not None:
            update_expression += ", user_personality_test = :personality_test"
            expression_values[':personality_test'] = user_personality_test
            
        if profile_id is not None:
            update_expression += ", profile_id = :profile_id"
            expression_values[':profile_id'] = profile_id
        
        table.update_item(
            Key={'user_id': user_id},
            UpdateExpression=update_expression,
            ExpressionAttributeValues=expression_values
        )
        
        sys.stderr.write(f"✅ Preferencias actualizadas para usuario: {user_id}\n")
        return {'success': True, 'message': 'Preferencias actualizadas correctamente'}
        
    except Exception as e:
        error_message = f"Error al actualizar preferencias: {e}"
        sys.stderr.write(f"❌ {error_message}\n")
        return {'success': False, 'error': error_message}


def delete_user_preferences(user_id: str) -> Dict:
    """
    Elimina las preferencias del usuario de DynamoDB.
    """
    if not DYNAMODB_AVAILABLE:
        return {'success': False, 'error': 'DynamoDB no está disponible.'}

    try:
        table = dynamodb.Table(PREFERENCES_TABLE_NAME)
        table.delete_item(Key={'user_id': user_id})
        
        sys.stderr.write(f"✅ Preferencias eliminadas para usuario: {user_id}\n")
        return {'success': True, 'message': 'Preferencias eliminadas correctamente'}
        
    except Exception as e:
        error_message = f"Error al eliminar preferencias: {e}"
        sys.stderr.write(f"❌ {error_message}\n")
        return {'success': False, 'error': error_message}


if __name__ == "__main__":
    import sys
    import json
    # Permite ejecutar funciones desde la línea de comandos para Node.js
    if len(sys.argv) >= 3:
        action = sys.argv[1]
        user_id = sys.argv[2]
        if action == "get":
            result = get_user_preferences(user_id)
            print(json.dumps(result))
        elif action == "save":
            tts_prefs = json.loads(sys.argv[3])
            personality_test = json.loads(sys.argv[4])
            profile_id = sys.argv[5] if len(sys.argv) > 5 else None
            result = save_user_preferences(user_id, tts_prefs, personality_test, profile_id)
            print(json.dumps(result))
        elif action == "update":
            tts_prefs = json.loads(sys.argv[3]) if len(sys.argv) > 3 else None
            personality_test = json.loads(sys.argv[4]) if len(sys.argv) > 4 else None
            profile_id = sys.argv[5] if len(sys.argv) > 5 else None
            result = update_user_preferences(user_id, tts_prefs, personality_test, profile_id)
            print(json.dumps(result))
        elif action == "delete":
            result = delete_user_preferences(user_id)
            print(json.dumps(result))
