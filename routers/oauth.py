from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from pydantic import BaseModel # Added
from sqlalchemy.orm import Session
from database import get_db
from models.user import User
import os
import httpx
from urllib.parse import urlencode
from jose import jwt
from datetime import datetime, timedelta, timezone
from passlib.context import CryptContext
from dotenv import load_dotenv
from google.oauth2 import id_token # Added
from google.auth.transport import requests as google_requests # Added

load_dotenv() # Load environment variables from .env file

router = APIRouter(prefix="/oauth", tags=["oauth"])

# Load environment variables
APP_BASE_URL = os.getenv("APP_BASE_URL")

GOOGLE_CLIENT_ANDROID_ID = os.getenv("GOOGLE_CLIENT_ANDROID_ID")
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_REDIRECT_URI = f"{APP_BASE_URL}/oauth/google/callback" if APP_BASE_URL else None

NAVER_CLIENT_ID = os.getenv("NAVER_CLIENT_ID")
NAVER_CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET")
NAVER_REDIRECT_URI = f"{APP_BASE_URL}/oauth/naver/callback" if APP_BASE_URL else None

KAKAO_CLIENT_ID = os.getenv("KAKAO_CLIENT_ID")
KAKAO_CLIENT_SECRET = os.getenv("KAKAO_CLIENT_SECRET")
KAKAO_REDIRECT_URI = f"{APP_BASE_URL}/oauth/kakao/callback" if APP_BASE_URL else None

# JWT Settings
SECRET_KEY = os.getenv("SECRET_KEY", "super-secret-key") # Change this in production!
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

# --- Google OAuth ---
@router.get("/google/login")
async def google_login():
    if not GOOGLE_CLIENT_ID or not GOOGLE_REDIRECT_URI:
        raise HTTPException(status_code=500, detail="Google OAuth configuration missing.")
    
    params = {
        "response_type": "code",
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "select_account"
    }
    return Response(headers={"Location": f"https://accounts.google.com/o/oauth2/auth?{urlencode(params)}"}, status_code=302)

@router.get("/google/callback")
async def google_callback(code: str, db: Session = Depends(get_db)):
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
        userinfo_response.raise_for_status()
        user_data = userinfo_response.json()

        user = db.query(User).filter(User.google_id == user_data["sub"]).first()

        if not user:
            # Create new user
            user = User(
                email=user_data["email"],
                username=user_data["name"],
                google_id=user_data["sub"],
                hashed_password="oauth_user_no_password" # Placeholder for OAuth users
            )
            db.add(user)
            db.commit()
            db.refresh(user)

        access_token = create_access_token(data={"sub": str(user.id)})
        return {"access_token": access_token, "token_type": "bearer"}

# --- Naver OAuth ---
@router.get("/naver/login")
async def naver_login():
    if not NAVER_CLIENT_ID or not NAVER_REDIRECT_URI:
        raise HTTPException(status_code=500, detail="Naver OAuth configuration missing.")

    params = {
        "response_type": "code",
        "client_id": NAVER_CLIENT_ID,
        "redirect_uri": NAVER_REDIRECT_URI,
        "state": "STATE_STRING", # You should generate a random state for security
    }
    return Response(headers={"Location": f"https://nid.naver.com/oauth2.0/authorize?{urlencode(params)}"}, status_code=302)

@router.get("/naver/callback")
async def naver_callback(code: str, state: str, db: Session = Depends(get_db)):
    if not NAVER_CLIENT_ID or not NAVER_CLIENT_SECRET or not NAVER_REDIRECT_URI:
        raise HTTPException(status_code=500, detail="Naver OAuth configuration missing.")

    # TODO: Verify state for security

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
        naver_email = user_data["response"].get("email")
        naver_nickname = user_data["response"].get("nickname")

        user = db.query(User).filter(User.naver_id == naver_user_id).first()

        if not user:
            # Create new user
            user = User(
                email=naver_email,
                username=naver_nickname or naver_email, # Use nickname if available, else email
                naver_id=naver_user_id,
                hashed_password="oauth_user_no_password" # Placeholder for OAuth users
            )
            db.add(user)
            db.commit()
            db.refresh(user)

        access_token = create_access_token(data={"sub": str(user.id)})
        return {"access_token": access_token, "token_type": "bearer"}

# --- Kakao OAuth ---
@router.get("/kakao/login")
async def kakao_login():
    if not KAKAO_CLIENT_ID or not KAKAO_REDIRECT_URI:
        raise HTTPException(status_code=500, detail="Kakao OAuth configuration missing.")

    params = {
        "response_type": "code",
        "client_id": KAKAO_CLIENT_ID,
        "redirect_uri": KAKAO_REDIRECT_URI,
    }
    return Response(headers={"Location": f"https://kauth.kakao.com/oauth/authorize?{urlencode(params)}"}, status_code=302)

@router.get("/kakao/callback")
async def kakao_callback(code: str, db: Session = Depends(get_db)):
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
        kakao_email = user_data["kakao_account"].get("email")
        kakao_nickname = user_data["properties"].get("nickname")

        user = db.query(User).filter(User.kakao_id == kakao_user_id).first()

        if not user:
            # Create new user
            user = User(
                email=kakao_email,
                username=kakao_nickname or kakao_email, # Use nickname if available, else email
                kakao_id=kakao_user_id,
                hashed_password="oauth_user_no_password" # Placeholder for OAuth users
            )
            db.add(user)
            db.commit()
            db.refresh(user)

        access_token = create_access_token(data={"sub": str(user.id)})
        return {"access_token": access_token, "token_type": "bearer"}

class Token(BaseModel):
    idToken: str

@router.post("/google/token")
async def google_token_signin(token: Token, db: Session = Depends(get_db)):
    if not GOOGLE_CLIENT_ANDROID_ID:
        raise HTTPException(status_code=500, detail="Google OAuth configuration missing.")
    print(token)
    try:
        idinfo = id_token.verify_oauth2_token(token.idToken, google_requests.Request(), GOOGLE_CLIENT_ID)

        userid = idinfo['sub']
        user = db.query(User).filter(User.google_id == userid).first()

        if not user:
            user = User(
                email=idinfo.get("email"),
                username=idinfo.get("name"),
                google_id=userid,
                hashed_password="oauth_user_no_password" # Placeholder for OAuth users
            )
            db.add(user)
            db.commit()
            db.refresh(user)

        access_token = create_access_token(data={"sub": str(user.id)})
        return {"access_token": access_token, "token_type": "bearer"}

    except ValueError:
        # Invalid token
        raise HTTPException(status_code=401, detail="Invalid Google token")
