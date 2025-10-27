from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials # Add HTTPBearer
from database import init_db # Changed import
from routers import (
    community, report, live_record, route, oauth, navigation, user, notice, calender
)
from models import User, Post, Comment, Report, Route
from starlette.staticfiles import StaticFiles # Add this import
from utils import events

from schemas import community as community_schema
from schemas import report as report_schema
from schemas import route as route_schema

community_schema.PostResponse.model_rebuild()
report_schema.ReportWithRouteResponse.model_rebuild()
route_schema.RouteWithReportsResponse.model_rebuild()

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

# Define the HTTPBearer scheme
oauth2_scheme = HTTPBearer()

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
# Apply HTTPBearer dependency to authenticated routers
app.include_router(community.router, dependencies=[Depends(oauth2_scheme)])
app.include_router(report.router, dependencies=[Depends(oauth2_scheme)])
app.include_router(live_record.router)
app.include_router(route.router, dependencies=[Depends(oauth2_scheme)])
app.include_router(oauth.router) # OAuth router handles authentication itself, no need for external dependency
app.include_router(navigation.router, dependencies=[Depends(oauth2_scheme)])
app.include_router(user.router, dependencies=[Depends(oauth2_scheme)])
app.include_router(notice.router, dependencies=[Depends(oauth2_scheme)])
app.include_router(calender.router, dependencies=[Depends(oauth2_scheme)])

# =========================
# 루트 엔드포인트
# =========================
@app.get("/")
def root():
    return {"message": "Welcome to Pedal App MVP"}

# 야호