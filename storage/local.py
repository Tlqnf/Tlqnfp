import os
import shutil
from fastapi import UploadFile
from .base import BaseStorage
from typing import Optional

# Assume a directory for uploads
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

class LocalStorage(BaseStorage):
    def save(self, file: UploadFile, filename: str, folder: Optional[str] = None) -> str:
        target_dir = UPLOAD_DIR
        if folder:
            target_dir = os.path.join(UPLOAD_DIR, folder)
            os.makedirs(target_dir, exist_ok=True) # Create subfolder if it doesn't exist

        file_path = os.path.join(target_dir, filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        # In a real app, this URL should be based on the server's domain
        return f"/{file_path}"

    def delete(self, file_url: str) -> None:
        # file_url will be like /uploads/board/image.png
        # Remove the leading '/'
        relative_path = file_url.lstrip('/')
        if os.path.exists(relative_path):
            os.remove(relative_path)
        else:
            print(f"File not found for deletion: {relative_path}") # Or log a warning
