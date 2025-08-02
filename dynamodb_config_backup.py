import boto3
import uuid
from datetime import datetime
import os
from typing import Optional, Dict, List
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

class DynamoDBManager:
    """
    Gestor para operaciones de DynamoDB en el proyecto Clutch.
    Almacena análisis de comunicación, preferencias de usuario y estadísticas.
    """
    
    def __init__(self):
        # Configuración desde variables de entorno
        self.region = os.getenv('AWS_REGION', 'us-east-1')
        self.table_name = os.getenv('DYNAMODB_TABLE_NAME', 'ClutchAnalysis')
        
        # Configuración de DynamoDB (soporta Local y AWS)
        dynamodb_config = {
            'region_name': self.region,
            'aws_access_key_id': os.getenv('AWS_ACCESS_KEY_ID'),
            'aws_secret_access_key': os.getenv('AWS_SECRET_ACCESS_KEY')
        }
        
        # Si hay endpoint local, úsalo (DynamoDB Local)
        endpoint_url = os.getenv('DYNAMODB_ENDPOINT')
        if endpoint_url:
            dynamodb_config['endpoint_url'] = endpoint_url
            print(f"🔧 Conectando a DynamoDB Local: {endpoint_url}")
        else:
            print(f"☁️ Conectando a AWS DynamoDB en región: {self.region}")
          # Conexión a DynamoDB
        try:
            self.dynamodb = boto3.resource('dynamodb', **dynamodb_config)
            self.table = self.dynamodb.Table(self.table_name)
            print(f"✅ Conexión exitosa a tabla: {self.table_name}")
        except Exception as e:
            print(f"❌ Error conectando a DynamoDB: {e}")
            self.dynamodb = None
            self.table = None
    
    def save_analysis(self, user_id: str, analysis_text: str, 
                     transcription: str = "", audio_s3_key: str = "",
                     user_preferences: Dict = None) -> str:
        """
        Guarda un análisis completo de comunicación en DynamoDB.
        
        Args:
            user_id: ID del usuario de Discord
            analysis_text: Texto del análisis generado por GPT
            transcription: Transcripción del audio de Whisper
            audio_s3_key: Clave del archivo de audio en S3 (opcional)
            user_preferences: Preferencias del usuario (coach, voz, etc.)
        
        Returns:
            ID único del análisis guardado
        """
        if not self.table:
            print("⚠️ DynamoDB no disponible, análisis no guardado")
            return "local-" + str(uuid.uuid4())
        
        analysis_id = str(uuid.uuid4())
        timestamp = datetime.utcnow().isoformat()
        
        item = {
            'id': analysis_id,
            'user_id': user_id,
            'analysis': analysis_text,
            'transcription': transcription,
            'timestamp': timestamp,
            'created_date': datetime.utcnow().strftime('%Y-%m-%d'),
            'type': 'communication_analysis'
        }
        
        # Agregar campos opcionales si están presentes
        if audio_s3_key:
            item['audio_s3_key'] = audio_s3_key
        
        if user_preferences:
            item['user_preferences'] = user_preferences
        
        try:
            response = self.table.put_item(Item=item)
            print(f"✅ Análisis guardado en DynamoDB: {analysis_id}")
            return analysis_id
        except Exception as e:
            print(f"❌ Error guardando análisis en DynamoDB: {e}")
            return "error-" + str(uuid.uuid4())
      def get_user_analyses(self, user_id: str, limit: int = 10) -> List[Dict]:
        """
        Obtiene los últimos análisis de un usuario específico.
        
        Args:
            user_id: ID del usuario
            limit: Número máximo de análisis a retornar
        
        Returns:
            Lista de análisis ordenados por fecha (más reciente primero)
        """
        if not self.table:
            print("⚠️ DynamoDB no disponible")
            return []
            
        try:
            response = self.table.scan(
                FilterExpression=boto3.dynamodb.conditions.Attr('user_id').eq(user_id),
                Limit=limit
            )
            
            # Ordenar por timestamp descendente
            analyses = sorted(
                response.get('Items', []), 
                key=lambda x: x.get('timestamp', ''), 
                reverse=True
            )
            
            return analyses[:limit]
        except Exception as e:
            print(f"❌ Error obteniendo análisis del usuario {user_id}: {e}")
            return []
      def get_user_stats(self, user_id: str) -> Dict:
        """
        Calcula estadísticas del usuario basadas en sus análisis históricos.
        
        Args:
            user_id: ID del usuario
        
        Returns:
            Diccionario con estadísticas del usuario
        """
        if not self.table:
            print("⚠️ DynamoDB no disponible")
            return {'total_analyses': 0, 'error': 'database_unavailable'}
            
        analyses = self.get_user_analyses(user_id, limit=50)
        
        if not analyses:
            return {
                'total_analyses': 0,
                'first_analysis': None,
                'latest_analysis': None,
                'improvement_trend': 'insufficient_data'
            }
        
        stats = {
            'total_analyses': len(analyses),
            'first_analysis': analyses[-1].get('timestamp') if analyses else None,
            'latest_analysis': analyses[0].get('timestamp') if analyses else None,
            'analyses_this_week': len([
                a for a in analyses 
                if self._is_within_days(a.get('timestamp'), 7)
            ]),
            'analyses_this_month': len([
                a for a in analyses 
                if self._is_within_days(a.get('timestamp'), 30)
            ])
        }
        
        return stats
      def save_user_session(self, user_id: str, session_data: Dict) -> str:
        """
        Guarda datos de una sesión específica (útil para tracking de mejoras).
        
        Args:
            user_id: ID del usuario
            session_data: Datos de la sesión (duración de audio, palabras clave, etc.)
        
        Returns:
            ID de la sesión guardada
        """
        if not self.table:
            print("⚠️ DynamoDB no disponible, sesión no guardada")
            return "local-session-" + str(uuid.uuid4())
            
        session_id = str(uuid.uuid4())
        timestamp = datetime.utcnow().isoformat()
        
        item = {
            'id': session_id,
            'user_id': user_id,
            'session_data': session_data,
            'timestamp': timestamp,
            'type': 'user_session'
        }
        
        try:
            response = self.table.put_item(Item=item)
            print(f"✅ Sesión guardada: {session_id}")
            return session_id
        except Exception as e:
            print(f"❌ Error guardando sesión: {e}")
            return "error-session-" + str(uuid.uuid4())
    
    def _is_within_days(self, timestamp_str: str, days: int) -> bool:
        """Verifica si un timestamp está dentro de los últimos N días."""
        try:
            from datetime import datetime, timedelta
            timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            cutoff = datetime.utcnow() - timedelta(days=days)
            return timestamp >= cutoff
        except:
            return False

# Instancia global para uso en el proyecto
dynamodb_manager = DynamoDBManager()

# Función de compatibilidad con el código original
def save_analysis(user_id: str, s3_key: str, analysis_text: str):
    """
    Función de compatibilidad con el código original.
    Guarda un análisis usando el manager de DynamoDB.
    """
    return dynamodb_manager.save_analysis(
        user_id=user_id,
        analysis_text=analysis_text,
        audio_s3_key=s3_key
    )
