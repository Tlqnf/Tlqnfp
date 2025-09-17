from abc import ABC, abstractmethod
from fastapi import UploadFile

class BaseStorage(ABC):
    @abstractmethod
    def save(self, file: UploadFile, filename: str) -> str:
        """Saves the file and returns the URL."""
        pass
