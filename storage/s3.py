import os
import boto3
from fastapi import UploadFile
from botocore.exceptions import NoCredentialsError
from .base import BaseStorage

# Get S3 config from environment variables
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_REGION = os.getenv("AWS_REGION")

class S3Storage(BaseStorage):
    def __init__(self):
        if not all([S3_BUCKET_NAME, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_REGION]):
            raise ValueError("S3 environment variables are not fully set.")
        self.s3_client = boto3.client(
            "s3",
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
            region_name=AWS_REGION
        )
        self.bucket_name = S3_BUCKET_NAME

    def save(self, file: UploadFile, filename: str) -> str:
        try:
            self.s3_client.upload_fileobj(
                file.file,
                self.bucket_name,
                filename,
                ExtraArgs={'ContentType': file.content_type}
            )
            # Return the public URL of the file
            return f"https://{self.bucket_name}.s3.{AWS_REGION}.amazonaws.com/{filename}"
        except NoCredentialsError:
            raise Exception("AWS credentials not available.")
