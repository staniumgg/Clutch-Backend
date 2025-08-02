"""
Integración con Amazon S3 para almacenar archivos de audio del proyecto Clutch.
Este módulo maneja la subida y gestión de archivos de audio en S3.
"""
import boto3
import os
from datetime import datetime
from dotenv import load_dotenv
from botocore.exceptions import ClientError, NoCredentialsError
import sys

# Cargar variables de entorno
load_dotenv()

class S3Manager:
    """
    Gestor para operaciones con Amazon S3 en el proyecto Clutch.
    """
    def __init__(self):
        self.region = os.getenv('AWS_REGION')
        self.bucket_name = os.getenv('S3_BUCKET_NAME')
        
        if not self.region or not self.bucket_name:
            sys.stderr.write("[ERROR_S3] AWS_REGION y S3_BUCKET_NAME deben estar en .env\n")
            self.s3_client = None
            self.available = False
            return

        try:
            self.s3_client = boto3.client(
                's3',
                region_name=self.region,
                aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
                aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
            )
            sys.stderr.write(f"[OK_S3] Conectado a S3 en region: {self.region}\n")
            self.available = True
        except (NoCredentialsError, ClientError) as e:
            sys.stderr.write(f"[ERROR_S3] Error conectando a S3: {e}\n")
            self.s3_client = None
            self.available = False

    def upload_audio_from_bytes(self, audio_data: bytes, user_id: str, base_filename: str, content_type: str = 'audio/mpeg') -> str:
        """
        Sube datos de audio en bytes a S3 y retorna la URL pública.
        """
        if not self.available:
            sys.stderr.write("⚠️ S3 no disponible, archivo no subido\n")
            return ""
        
        try:
            date_folder = datetime.now().strftime('%Y/%m/%d')
            s3_key = f"audios/{date_folder}/user_{user_id}_{base_filename}"
            
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=audio_data,
                ContentType=content_type,
                Metadata={
                    'user_id': str(user_id)
                }
            )
            
            # Construir la URL pública
            url = f"https://{self.bucket_name}.s3.{self.region}.amazonaws.com/{s3_key}"
            sys.stderr.write(f"✅ Audio subido a S3: {url}\n")
            return url
            
        except ClientError as e:
            sys.stderr.write(f"❌ Error subiendo a S3: {e}\n")
            return ""

s3_manager = S3Manager()
