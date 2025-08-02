import boto3
import uuid
from datetime import datetime
import os
from typing import Optional, Dict, List
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Configuración de DynamoDB
region = os.getenv('AWS_REGION', 'us-east-1')
table_name = os.getenv('DYNAMODB_TABLE_NAME', 'ClutchAnalysis')

# Conexión a DynamoDB
try:
    dynamodb = boto3.resource(
        'dynamodb', 
        region_name=region,
        aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
    )
    print(f"✅ Conectado a DynamoDB en región: {region}")
except Exception as e:
    print(f"❌ Error conectando a DynamoDB: {e}")
    dynamodb = None

def save_analysis(user_id: str, s3_key: str, analysis_text: str):
    """
    Guarda un análisis en DynamoDB usando la estructura simple propuesta.
    
    Args:
        user_id: ID del usuario de Discord
        s3_key: Clave del archivo de audio en S3 (puede ser vacío)
        analysis_text: Texto del análisis generado por GPT
    
    Returns:
        ID único del análisis guardado
    """
    if not dynamodb:
        print("⚠️ DynamoDB no disponible, análisis no guardado")
        return "local-" + str(uuid.uuid4())
    
    try:
        table = dynamodb.Table(table_name)
        
        item = {
            'id': str(uuid.uuid4()),
            'user_id': user_id,
            'audio_s3_key': s3_key,
            'analysis': analysis_text,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        response = table.put_item(Item=item)
        print("✅ Análisis guardado:", response)
        return item['id']
        
    except Exception as e:
        print(f"❌ Error guardando análisis: {e}")
        return "error-" + str(uuid.uuid4())

class DynamoDBManager:
    """
    Gestor para operaciones de DynamoDB en el proyecto Clutch.
    Mantiene compatibilidad con el código existente.
    """
    
    def __init__(self):
        self.dynamodb = dynamodb
        self.table_name = table_name
        self.table = dynamodb.Table(table_name) if dynamodb else None
    
    def save_analysis(self, user_id: str, analysis_text: str, 
                     transcription: str = "", audio_s3_key: str = "",
                     user_preferences: Dict = None) -> str:
        """
        Método mejorado que usa la función simple save_analysis.
        """
        # Usar la función simple para guardar
        analysis_id = save_analysis(user_id, audio_s3_key, analysis_text)
        
        # Si hay transcripción o preferencias, guardar información adicional
        if transcription or user_preferences:
            try:
                if self.table:
                    # Actualizar el item con información adicional
                    update_expression = "SET "
                    expression_values = {}
                    
                    if transcription:
                        update_expression += "transcription = :trans, "
                        expression_values[':trans'] = transcription
                    
                    if user_preferences:
                        update_expression += "user_preferences = :prefs, "
                        expression_values[':prefs'] = user_preferences
                    
                    # Remover la última coma
                    update_expression = update_expression.rstrip(', ')
                    
                    if expression_values:
                        self.table.update_item(
                            Key={'id': analysis_id},
                            UpdateExpression=update_expression,
                            ExpressionAttributeValues=expression_values
                        )
                        print("📝 Información adicional guardada")
            except Exception as e:
                print(f"⚠️ Error guardando información adicional: {e}")
        
        return analysis_id
    
    def get_user_analyses(self, user_id: str, limit: int = 10) -> List[Dict]:
        """Obtiene los últimos análisis de un usuario."""
        if not self.table:
            return []
            
        try:
            response = self.table.scan(
                FilterExpression=boto3.dynamodb.conditions.Attr('user_id').eq(user_id),
                Limit=limit
            )
            
            analyses = sorted(
                response.get('Items', []), 
                key=lambda x: x.get('timestamp', ''), 
                reverse=True
            )
            
            return analyses[:limit]
        except Exception as e:
            print(f"❌ Error obteniendo análisis: {e}")
            return []
    
    def get_user_stats(self, user_id: str) -> Dict:
        """Calcula estadísticas del usuario."""
        if not self.table:
            return {'total_analyses': 0, 'error': 'database_unavailable'}
            
        analyses = self.get_user_analyses(user_id, limit=50)
        
        if not analyses:
            return {
                'total_analyses': 0,
                'first_analysis': None,
                'latest_analysis': None
            }
        
        return {
            'total_analyses': len(analyses),
            'first_analysis': analyses[-1].get('timestamp') if analyses else None,
            'latest_analysis': analyses[0].get('timestamp') if analyses else None
        }

# Instancia global para compatibilidad
dynamodb_manager = DynamoDBManager()
