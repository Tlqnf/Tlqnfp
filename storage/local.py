import os
import shutil
from fastapi import UploadFile
from .base import BaseStorage

# Assume a directory for uploads
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

class LocalStorage(BaseStorage):
    def save(self, file: UploadFile, filename: str) -> str:
        file_path = os.path.join(UPLOAD_DIR, filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        # In a real app, this URL should be based on the server's domain
        return f"/{file_path}"
