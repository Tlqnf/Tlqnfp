from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session

from database import get_db
from schemas import subscription as subscription_schema
from services import subscription as subscription_service

router = APIRouter(
    prefix="/subscriptions",
    tags=["subscriptions"],
)

@router.post("/webhook/google", status_code=status.HTTP_204_NO_CONTENT)
async def google_play_webhook(
    payload: subscription_schema.PubSubPush,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Handles Real-Time Developer Notifications (RTDN) from Google Play,
    pushed via Google Cloud Pub/Sub.
    
    Google expects a 204 No Content response on successful receipt of the message.
    The actual processing is done in the background to ensure a timely response.
    """
    try:
        # The actual data is in the `data` field of the message, base64-encoded.
        message_data = payload.message.data
        
        # Add the processing to background tasks to avoid blocking
        # and to ensure we can send a timely 204 response to Google.
        background_tasks.add_task(subscription_service.process_pubsub_message, db, message_data)
        
        return
        
    except Exception as e:
        # This is a fallback. Ideally, the background task handles its own errors.
        # If the payload is malformed, Pydantic will raise a validation error
        # before this point, and FastAPI will return a 422 response.
        print(f"Error in webhook endpoint: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to process webhook payload."
        )

