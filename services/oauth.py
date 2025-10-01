
from fastapi import HTTPException
from sqlalchemy.orm import Session
from models.user import User
import os
import httpx
from jose import jwt
from datetime import datetime, timedelta
from passlib.context import CryptContext
from dotenv import load_dotenv
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

load_dotenv()

APP_BASE_URL = os.getenv("APP_BASE_URL")

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_REDIRECT_URI = f"{APP_BASE_URL}/oauth/google/callback" if APP_BASE_URL else None

NAVER_CLIENT_ID = os.getenv("NAVER_CLIENT_ID")
NAVER_CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET")
NAVER_REDIRECT_URI = f"{APP_BASE_URL}/oauth/naver/callback" if APP_BASE_URL else None

KAKAO_CLIENT_ID = os.getenv("KAKAO_CLIENT_ID")
KAKAO_CLIENT_SECRET = os.getenv("KAKAO_CLIENT_SECRET")
KAKAO_REDIRECT_URI = f"{APP_BASE_URL}/oauth/kakao/callback" if APP_BASE_URL else None

SECRET_KEY = os.getenv("SECRET_KEY", "super-secret-key")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 300000

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def handle_google_callback(code: str, db: Session):
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET or not GOOGLE_REDIRECT_URI:
        raise HTTPException(status_code=500, detail="Google OAuth configuration missing.")

    token_url = "https://oauth2.googleapis.com/token"
    token_params = {
        "code": code,
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "grant_type": "authorization_code",
    }

    async with httpx.AsyncClient() as client:
        token_response = await client.post(token_url, data=token_params)
        token_response.raise_for_status()
        token_data = token_response.json()
        access_token = token_data["access_token"]

        userinfo_url = "https://www.googleapis.com/oauth2/v3/userinfo"
        userinfo_response = await client.get(userinfo_url, headers={
            "Authorization": f"Bearer {access_token}"
        })
        user_data = userinfo_response.json()

        google_id = user_data["sub"]
        email = user_data["email"]
        username = user_data["name"]

        user = db.query(User).filter(User.google_id == google_id).first()

        if user:
            pass
        else:
            user = db.query(User).filter(User.email == email).first()
            if user:
                if not user.google_id:
                    user.google_id = google_id
                    db.add(user)
                    db.commit()
                    db.refresh(user)
            else:
                user = User(
                    email=email,
                    username=username,
                    google_id=google_id,
                    hashed_password="oauth_user_no_password"
                )
                db.add(user)
                db.commit()
                db.refresh(user)

        access_token = create_access_token(data={"sub": str(user.id)})
        return {"access_token": access_token, "token_type": "bearer"}

async def handle_naver_callback(code: str, state: str, db: Session):
    if not NAVER_CLIENT_ID or not NAVER_CLIENT_SECRET or not NAVER_REDIRECT_URI:
        raise HTTPException(status_code=500, detail="Naver OAuth configuration missing.")

    token_url = "https://nid.naver.com/oauth2.0/token"
    token_params = {
        "grant_type": "authorization_code",
        "client_id": NAVER_CLIENT_ID,
        "client_secret": NAVER_CLIENT_SECRET,
        "redirect_uri": NAVER_REDIRECT_URI,
        "code": code,
        "state": state,
    }

    async with httpx.AsyncClient() as client:
        token_response = await client.post(token_url, data=token_params)
        token_response.raise_for_status()
        token_data = token_response.json()
        access_token = token_data["access_token"]

        userinfo_url = "https://openapi.naver.com/v1/nid/me"
        userinfo_response = await client.get(userinfo_url, headers={
            "Authorization": f"Bearer {access_token}"
        })
        userinfo_response.raise_for_status()
        user_data = userinfo_response.json()
        naver_user_id = user_data["response"]["id"]
        email = user_data["response"].get("email")
        username = user_data["response"].get("nickname") or email

        user = db.query(User).filter(User.naver_id == naver_user_id).first()

        if user:
            pass
        else:
            user = db.query(User).filter(User.email == email).first()
            if user:
                if not user.naver_id:
                    user.naver_id = naver_user_id
                    db.add(user)
                    db.commit()
                    db.refresh(user)
            else:
                user = User(
                    email=email,
                    username=username,
                    naver_id=naver_user_id,
                    hashed_password="oauth_user_no_password"
                )
                db.add(user)
                db.commit()
                db.refresh(user)

        access_token = create_access_token(data={"sub": str(user.id)})
        return {"access_token": access_token, "token_type": "bearer"}

async def handle_kakao_callback(code: str, db: Session):
    if not KAKAO_CLIENT_ID or not KAKAO_CLIENT_SECRET or not KAKAO_REDIRECT_URI:
        raise HTTPException(status_code=500, detail="Kakao OAuth configuration missing.")

    token_url = "https://kauth.kakao.com/oauth/token"
    token_params = {
        "grant_type": "authorization_code",
        "client_id": KAKAO_CLIENT_ID,
        "client_secret": KAKAO_CLIENT_SECRET,
        "redirect_uri": KAKAO_REDIRECT_URI,
        "code": code,
    }

    async with httpx.AsyncClient() as client:
        token_response = await client.post(token_url, data=token_params)
        token_response.raise_for_status()
        token_data = token_response.json()
        access_token = token_data["access_token"]

        userinfo_url = "https://kapi.kakao.com/v2/user/me"
        userinfo_response = await client.get(userinfo_url, headers={
            "Authorization": f"Bearer {access_token}"
        })
        userinfo_response.raise_for_status()
        user_data = userinfo_response.json()
        kakao_user_id = str(user_data["id"])
        email = user_data["kakao_account"].get("email")
        username = user_data["properties"].get("nickname") or email

        user = db.query(User).filter(User.kakao_id == kakao_user_id).first()

        if user:
            pass
        else:
            user = db.query(User).filter(User.email == email).first()
            if user:
                if not user.kakao_id:
                    user.kakao_id = kakao_user_id
                    db.add(user)
                    db.commit()
                    db.refresh(user)
            else:
                user = User(
                    email=email,
                    username=username,
                    kakao_id=kakao_user_id,
                    hashed_password="oauth_user_no_password"
                )
                db.add(user)
                db.commit()
                db.refresh(user)

        access_token = create_access_token(data={"sub": str(user.id)})
        return {"access_token": access_token, "token_type": "bearer"}

async def handle_google_token_signin(token: str, db: Session):
    GOOGLE_CLIENT_ANDROID_ID = os.getenv("GOOGLE_CLIENT_ANDROID_ID")
    if not GOOGLE_CLIENT_ANDROID_ID:
        raise HTTPException(status_code=500, detail="Google OAuth configuration missing.")

    try:
        idinfo = id_token.verify_oauth2_token(token, google_requests.Request(), GOOGLE_CLIENT_ID)

        google_id = idinfo['sub']
        email = idinfo.get("email")
        username = idinfo.get("name")

        user = db.query(User).filter(User.google_id == google_id).first()

        if user:
            pass
        else:
            user = db.query(User).filter(User.email == email).first()
            if user:
                if not user.google_id:
                    user.google_id = google_id
                    db.add(user)
                    db.commit()
                    db.refresh(user)
            else:
                user = User(
                    email=email,
                    username=username,
                    google_id=google_id,
                    hashed_password="oauth_user_no_password"
                )
                db.add(user)
                db.commit()
                db.refresh(user)

        access_token = create_access_token(data={"sub": str(user.id)})
        return {"access_token": access_token, "token_type": "bearer"}

    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid Google token")

async def handle_kakao_token_signin(kakao_token: str, db: Session):
    if not KAKAO_CLIENT_ID:
        raise HTTPException(status_code=500, detail="Kakao OAuth configuration missing.")

    try:
        userinfo_url = "https://kapi.kakao.com/v2/user/me"
        async with httpx.AsyncClient() as client:
            userinfo_response = await client.get(userinfo_url, headers={
                "Authorization": f"Bearer {kakao_token}"
            })
            userinfo_response.raise_for_status()
            user_data = userinfo_response.json()

        kakao_user_id = str(user_data["id"])
        email = user_data["kakao_account"].get("email")
        username = user_data["properties"].get("nickname") or email

        user = db.query(User).filter(User.kakao_id == kakao_user_id).first()

        if user:
            pass
        else:
            user = db.query(User).filter(User.email == email).first()
            if user:
                if not user.kakao_id:
                    user.kakao_id = kakao_user_id
                    db.add(user)
                    db.commit()
                    db.refresh(user)
            else:
                user = User(
                    email=email,
                    username=username,
                    kakao_id=kakao_user_id,
                    hashed_password="oauth_user_no_password"
                )
                db.add(user)
                db.commit()
                db.refresh(user)

        access_token = create_access_token(data={"sub": str(user.id)})
        return {"access_token": access_token, "token_type": "bearer"}

    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=f"Kakao API error: {e.response.text}")
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Invalid Kakao token or other error: {e}")
