# api/src/utils/storage/__init__.py

import os
from typing import BinaryIO
import boto3
from botocore.client import Config

class StorageProvider:
    def __init__(self):
        self.endpoint = os.getenv("MINIO_ENDPOINT", "http://localhost:9000")
        self.access_key = os.getenv("MINIO_ROOT_USER", "minioadmin")
        self.secret_key = os.getenv("MINIO_ROOT_PASSWORD", "minioadmin")
        self.bucket = os.getenv("STORAGE_BUCKET", "burstdb-artifacts")
        
        self.s3 = boto3.client(
            's3',
            endpoint_url=self.endpoint,
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
            config=Config(signature_version='s3v4'),
            region_name='us-east-1'
        )
        self._ensure_bucket()

    def _ensure_bucket(self):
        try:
            self.s3.head_bucket(Bucket=self.bucket)
        except:
            self.s3.create_bucket(Bucket=self.bucket)

    def upload_file(self, object_name: str, data: BinaryIO):
        self.s3.put_object(Bucket=self.bucket, Key=object_name, Body=data)

    def get_download_url(self, object_name: str, expires_in: int = 3600):
        return self.s3.generate_presigned_url(
            'get_object',
            Params={'Bucket': self.bucket, 'Key': object_name},
            ExpiresIn=expires_in
        )

storage = StorageProvider()
