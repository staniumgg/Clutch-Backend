import boto3
import os
from botocore.exceptions import NoCredentialsError

class S3Manager:
    def __init__(self):
        self.bucket_name = os.getenv('S3_BUCKET_NAME')
        self.region = os.getenv('AWS_REGION')
        self.available = bool(self.bucket_name and self.region)
        if self.available:
            self.s3 = boto3.client(
                's3',
                region_name=self.region,
                aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
                aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
            )

    def upload_audio_from_bytes(self, audio_bytes, user_id, filename):
        if not self.available:
            return ''
        key = f"audios/{user_id}/{filename}"
        try:
            self.s3.put_object(Bucket=self.bucket_name, Key=key, Body=audio_bytes, ContentType='audio/mpeg')
            url = f"https://{self.bucket_name}.s3.{self.region}.amazonaws.com/{key}"
            return url
        except NoCredentialsError:
            return ''
        except Exception as e:
            print(f"Error uploading to S3: {e}")
            return ''

    def generate_presigned_url(self, user_id, filename, expires_in=300):
        if not self.available:
            return ''
        key = f"audios/{user_id}/{filename}"
        try:
            url = self.s3.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket_name, 'Key': key},
                ExpiresIn=expires_in
            )
            return url
        except Exception as e:
            print(f"Error generating presigned URL: {e}")
            return ''

s3_manager = S3Manager()
