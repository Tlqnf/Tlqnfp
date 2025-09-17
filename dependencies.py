import os
from functools import lru_cache
from fastapi import Depends
from storage.base import BaseStorage
from storage.local import LocalStorage
from storage.s3 import S3Storage

@lru_cache(maxsize=1)
def get_storage_manager_instance() -> BaseStorage:
    storage_type = os.getenv("STORAGE_TYPE", "local")
    if storage_type == "s3":
        return S3Storage()
    elif storage_type == "local":
        return LocalStorage()
    else:
        raise ValueError(f"Unknown storage type: {storage_type}")

def get_storage_manager(storage: BaseStorage = Depends(get_storage_manager_instance)) -> BaseStorage:
    return storage
