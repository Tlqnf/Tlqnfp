from typing import Optional

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

    def save(self, file: UploadFile, filename: str, folder: Optional[str] = None) -> str:
        try:
            s3_key = f"{folder}/{filename}" if folder else filename
            self.s3_client.upload_fileobj(
                file.file,
                self.bucket_name,
                s3_key,
                ExtraArgs={'ContentType': file.content_type}
            )
            # Return the public URL of the file
            return f"https://{self.bucket_name}.s3.{AWS_REGION}.amazonaws.com/{s3_key}"
        except NoCredentialsError:
            raise Exception("AWS credentials not available.")

    def delete(self, file_url: str) -> None:
        try:
            # Extract the S3 key from the file_url
            # Assuming file_url is in the format: https://<bucket_name>.s3.<region>.amazonaws.com/<s3_key>
            s3_key = "/".join(file_url.split("/")[3:])
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=s3_key)
        except NoCredentialsError:
            raise Exception("AWS credentials not available.")
        except Exception as e:
            print(f"Error deleting S3 object {file_url}: {e}") # Or log a warning
