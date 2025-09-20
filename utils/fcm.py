import firebase_admin
from firebase_admin import credentials, messaging
from sqlalchemy.orm import Session

from models.user import User

# Initialize Firebase Admin SDK (only once)
# Replace 'path/to/your/serviceAccountKey.json' with the actual path to your Firebase service account key file.
# It's recommended to store this path in an environment variable.
try:
    cred = credentials.Certificate('key/pedal-1e999-firebase-adminsdk-fbsvc-0dba55d5dc.json')
    firebase_admin.initialize_app(cred)
except ValueError:
    # App is already initialized, which can happen in development with hot-reloading
    pass

def send_push_notification(db: Session, user: User, device_token: str, message: str):
    try:
        message_obj = messaging.Message(
            notification=messaging.Notification(
                title='새로운 멘션 알림',
                body=message,
            ),
            token=device_token,
        )
        response = messaging.send(message_obj)
        print('Successfully sent message:', response)
    except messaging.UnregisteredError:
        print(f"FCM token for user {user.id} is unregistered. Clearing token.")
        user.fcm_token = None
        db.add(user)
        db.commit()
    except Exception as e:
        print(f"Error sending message: {e}")
