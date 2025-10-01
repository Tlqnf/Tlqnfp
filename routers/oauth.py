from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session
from database import get_db
import os
from urllib.parse import urlencode
from services import oauth as oauth_service

router = APIRouter(prefix="/oauth", tags=["oauth"])

APP_BASE_URL = os.getenv("APP_BASE_URL")

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_REDIRECT_URI = f"{APP_BASE_URL}/oauth/google/callback" if APP_BASE_URL else None

NAVER_CLIENT_ID = os.getenv("NAVER_CLIENT_ID")
NAVER_REDIRECT_URI = f"{APP_BASE_URL}/oauth/naver/callback" if APP_BASE_URL else None

KAKAO_CLIENT_ID = os.getenv("KAKAO_CLIENT_ID")
KAKAO_REDIRECT_URI = f"{APP_BASE_URL}/oauth/kakao/callback" if APP_BASE_URL else None

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
    return await oauth_service.handle_google_callback(code, db)

@router.get("/naver/login")
async def naver_login():
    if not NAVER_CLIENT_ID or not NAVER_REDIRECT_URI:
        raise HTTPException(status_code=500, detail="Naver OAuth configuration missing.")

    params = {
        "response_type": "code",
        "client_id": NAVER_CLIENT_ID,
        "redirect_uri": NAVER_REDIRECT_URI,
        "state": "STATE_STRING",
    }
    return Response(headers={"Location": f"https://nid.naver.com/oauth2.0/authorize?{urlencode(params)}"}, status_code=302)

@router.get("/naver/callback")
async def naver_callback(code: str, state: str, db: Session = Depends(get_db)):
    return await oauth_service.handle_naver_callback(code, state, db)

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
    return await oauth_service.handle_kakao_callback(code, db)

class Token(BaseModel):
    idToken: str

class KakaoToken(BaseModel):
    accessToken: str

@router.post("/google/token")
async def google_token_signin(token: Token, db: Session = Depends(get_db)):
    return await oauth_service.handle_google_token_signin(token.idToken, db)

@router.post("/kakao/token")
async def kakao_token_signin(kakao_token: KakaoToken, db: Session = Depends(get_db)):
    return await oauth_service.handle_kakao_token_signin(kakao_token.accessToken, db)