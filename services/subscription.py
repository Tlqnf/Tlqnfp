import os
import json
import base64
from datetime import datetime, timezone

from google.oauth2 import service_account
from googleapiclient.discovery import build
from sqlalchemy.orm import Session

from models import user as user_model
from schemas import subscription as subscription_schema

# --- Google API Setup ---
# Path to your service account key file.
# It's recommended to set this as an environment variable.
SERVICE_ACCOUNT_FILE = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

# Define the scope for the Android Publisher API.
SCOPES = ['https://www.googleapis.com/auth/androidpublisher']

def get_google_api_service():
    """Initializes and returns the Google Play Developer API service."""
    if not SERVICE_ACCOUNT_FILE:
        raise ValueError("GOOGLE_APPLICATION_CREDENTIALS environment variable not set.")
    
    credentials = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES
    )
    service = build('androidpublisher', 'v3', credentials=credentials)
    return service

# --- Subscription Logic ---

def handle_subscription_notification(db: Session, notification: subscription_schema.DeveloperNotification):
    """
    Processes a subscription notification from Google Play.
    """
    if not notification.subscription_notification:
        # Not a subscription notification, might be a test notification.
        # You can add handling for test notifications if needed.
        print("Received a non-subscription notification.")
        return

    sub_notification = notification.subscription_notification
    package_name = notification.package_name
    purchase_token = sub_notification.purchase_token
    subscription_id = sub_notification.subscription_id
    
    service = get_google_api_service()
    
    try:
        # Verify the purchase with Google
        purchase = service.purchases().subscriptions().get(
            packageName=package_name,
            subscriptionId=subscription_id,
            token=purchase_token
        ).execute()

        # The purchase is valid, now find the user and update their status
        # The purchase object contains `obfuscatedExternalAccountId` which you should have set to your user's ID when initiating the purchase.
        # This is the most reliable way to link a purchase to a user.
        user_id = purchase.get("obfuscatedExternalAccountId")
        if not user_id:
            # Fallback: If you don't have the account ID, you might need another way to link the user.
            # For this example, we'll try to find the user by the purchase token if they already have one.
            db_user = db.query(user_model.User).filter(user_model.User.google_purchase_token == purchase_token).first()
        else:
            db_user = db.query(user_model.User).filter(user_model.User.id == int(user_id)).first()

        if not db_user:
            print(f"User not found for purchase token: {purchase_token}")
            # Potentially save this transaction to a separate table for manual review
            return

        # Determine subscription status based on the notification type
        # and the purchase details.
        # Notification Types:
        # 1: SUBSCRIPTION_RECOVERED
        # 2: SUBSCRIPTION_RENEWED
        # 3: SUBSCRIPTION_CANCELED
        # 4: SUBSCRIPTION_PURCHASED
        # 5: SUBSCRIPTION_ON_HOLD
        # 6: SUBSCRIPTION_IN_GRACE_PERIOD
        # 7: SUBSCRIPTION_RESTARTED
        # 8: SUBSCRIPTION_PRICE_CHANGE_CONFIRMED
        # 9: SUBSCRIPTION_DEFERRED
        # 12: SUBSCRIPTION_REVOKED
        # 13: SUBSCRIPTION_EXPIRED

        notification_type = sub_notification.notification_type
        is_active = False

        if notification_type in [1, 2, 4, 7, 8]: # Active states
            is_active = True
        elif notification_type in [3, 5, 6, 9, 12, 13]: # Inactive/problematic states
            is_active = False

        # The `expiryTimeMillis` from the purchase object is the definitive expiry time.
        expiry_time_ms = int(purchase.get("expiryTimeMillis", 0))
        expiry_date = datetime.fromtimestamp(expiry_time_ms / 1000, tz=timezone.utc)

        # Update user record
        db_user.is_subscribed = is_active
        db_user.subscription_expiry_date = expiry_date
        db_user.google_purchase_token = purchase_token # Store the latest token
        
        db.commit()
        print(f"Successfully updated subscription for user {db_user.id}. Active: {is_active}, Expires: {expiry_date}")

    except Exception as e:
        print(f"An error occurred while processing subscription notification: {e}")
        # It's important to handle errors, perhaps by retrying later.
        # For now, we just print the error.
        db.rollback()

def process_pubsub_message(db: Session, data: str):
    """
    Decodes the Pub/Sub message and passes it to the handler.
    """
    # The data is base64-encoded JSON.
    decoded_data = base64.b64decode(data).decode("utf-8")
    notification_payload = json.loads(decoded_data)
    
    # Validate with Pydantic model
    developer_notification = subscription_schema.DeveloperNotification(**notification_payload)
    
    handle_subscription_notification(db, developer_notification)

