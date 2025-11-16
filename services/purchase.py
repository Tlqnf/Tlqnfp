import os
from google.oauth2 import service_account
from googleapiclient.discovery import build
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from models.user import User
from schemas.purchase import PurchaseVerificationRequest

# --- Configuration ---
# 환경 변수에서 서비스 계정 파일 경로와 패키지 이름을 가져옵니다.
# 실제 배포 환경에서는 이 값들을 안전하게 설정해야 합니다.
SERVICE_ACCOUNT_FILE = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")

# --- Google API Client ---
def get_google_api_client():
    """Google API 클라이언트를 생성하고 반환합니다."""
    if not SERVICE_ACCOUNT_FILE:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Google service account credentials are not configured.",
        )
    try:
        credentials = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE,
            scopes=["https://www.googleapis.com/auth/androidpublisher"],
        )
        return build("androidpublisher", "v3", credentials=credentials)
    except Exception as e:
        # In a real app, you'd want to log this error.
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initialize Google API client: {e}",
        )


def verify_google_purchase(
    db: Session, user_id: int, request: PurchaseVerificationRequest
):
    """
    Google Play에서 발생한 구매를 검증하고, 유효한 경우 사용자의 구독 상태를 업데이트합니다.
    """
    android_publisher = get_google_api_client()
    purchase_token = request.purchase_token
    product_id = request.product_id  # product_id는 현재 검증에 직접 사용되진 않지만, 로깅이나 추가 검증에 활용될 수 있습니다.
    package_name = request.package_name

    try:
        # Google Play Developer API를 호출하여 구독 정보 조회
        purchase_info = (
            android_publisher.purchases()
            .subscriptionsv2()
            .get(
                packageName=package_name,
                token=purchase_token,
            )
            .execute()
        )

        # 구독 상태 확인 (예: 'SUBSCRIPTION_STATE_ACTIVE')
        subscription_state = purchase_info.get("subscriptionState")
        if subscription_state != "SUBSCRIPTION_STATE_ACTIVE":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Subscription is not active. State: {subscription_state}",
            )

        # 확인(acknowledgement) 상태 확인
        # Google의 권장사항에 따라, 백엔드에서 확인 처리를 해야 합니다.
        acknowledgement_state = purchase_info.get("acknowledgementState")
        if acknowledgement_state == "ACKNOWLEDGEMENT_STATE_PENDING":
            android_publisher.purchases().subscriptions().acknowledge(
                packageName=package_name,
                subscriptionId=product_id,
                token=purchase_token,
                body={"developerPayload": f"Acknowledged by backend for user {user_id}"}
            ).execute()

        # 데이터베이스에서 사용자 조회 및 구독 상태 업데이트
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )

        user.is_subscribed = True
        db.commit()
        db.refresh(user)

        return {"message": "Purchase verified and user subscribed successfully."}

    except HTTPException as e:
        # Re-raise HTTPExceptions to be handled by FastAPI
        raise e
    except Exception as e:
        # In a real app, you'd want to log this error.
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred during purchase verification: {e}",
        )

