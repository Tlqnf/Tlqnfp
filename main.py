from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import init_db # Changed import
from routers import (
    community, report, live_record, route, oauth, navigation, user
)
from models import User, Post, Comment, Report, Route
from starlette.staticfiles import StaticFiles # Add this import

# =========================
# DB 초기화 (모델 기반 테이블 생성)
# =========================
init_db() # Call the function

# =========================
# FastAPI 앱 생성
# =========================
app = FastAPI(
    title="Pedal App MVP",
    description="MVP of Pedal App",
    version="0.1.0",
)

# =========================
# CORS 설정 (Flutter 앱 연동용)
# =========================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 실제 배포 시에는 Flutter 앱 도메인만 허용
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =========================
# Static Files Serving
# =========================
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads") # Add this

# =========================
# 라우터 등록
# =========================
app.include_router(community.router)
app.include_router(report.router)
app.include_router(live_record.router)
app.include_router(route.router)
app.include_router(oauth.router)
app.include_router(navigation.router)
app.include_router(user.router)

# =========================
# 루트 엔드포인트
# =========================
@app.get("/")
def root():
    return {"message": "Welcome to Pedal App MVP"}