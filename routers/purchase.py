from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from schemas.purchase import PurchaseVerificationRequest
from services import purchase as purchase_service
from models.user import User
from utils.auth import get_current_user

router = APIRouter(prefix="/purchase", tags=["purchase"])


@router.post("/google/verify", status_code=200)
def verify_google_purchase_endpoint(
    request: PurchaseVerificationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    앱에서 전달받은 Google Play 구매 토큰을 검증합니다.

    - **purchase_token**: Google Play에서 발급한 구매 토큰
    - **product_id**: 구매한 상품의 ID
    """
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")

    return purchase_service.verify_google_purchase(
        db=db, user_id=current_user.id, request=request
    )
