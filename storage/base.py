from abc import ABC, abstractmethod
from fastapi import UploadFile
from typing import Optional

class BaseStorage(ABC):
    @abstractmethod
    def save(self, file: UploadFile, filename: str, folder: Optional[str] = None) -> str:
        """Saves the file and returns the URL."""
        pass

    @abstractmethod
    def delete(self, file_url: str) -> None:
        """Deletes the file from the storage."""
        pass


