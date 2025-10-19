from abc import abstractmethod
from typing import List, Optional

from sqlalchemy.orm import Session

from schemas.community import PostResponse

class BoardSelectService:
    @abstractmethod
    def select(self, db: Session, user_lat: Optional[float] = None, user_lon: Optional[float] = None, page: int = 1, page_size: int = 10) -> List[PostResponse]:
        pass