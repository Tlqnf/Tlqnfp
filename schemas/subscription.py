from pydantic import BaseModel, Field
from typing import Optional

class SubscriptionNotification(BaseModel):
    """
    Represents the subscriptionNotification part of the Google Play RTDN.
    """
    version: str
    notification_type: int = Field(..., alias="notificationType")
    purchase_token: str = Field(..., alias="purchaseToken")
    subscription_id: str = Field(..., alias="subscriptionId")


class DeveloperNotification(BaseModel):
    """
    Represents the overall structure of a Real-Time Developer Notification (RTDN)
    from Google Play.
    """
    version: str
    package_name: str = Field(..., alias="packageName")
    event_time_millis: int = Field(..., alias="eventTimeMillis")
    subscription_notification: Optional[SubscriptionNotification] = Field(None, alias="subscriptionNotification")
    # test_notification: Optional[TestNotification] = Field(None, alias="testNotification") # Add if you need to handle test notifications


class PubSubMessage(BaseModel):
    """
    Represents the message part of a Pub/Sub push request.
    The `data` is a base64-encoded string containing the JSON of DeveloperNotification.
    """
    message_id: str = Field(..., alias="messageId")
    data: str
    publish_time: str = Field(..., alias="publishTime")


class PubSubPush(BaseModel):
    """
    Represents the full payload of a Pub/Sub push request.
    """
    message: PubSubMessage
    subscription: str

