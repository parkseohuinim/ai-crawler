from fastapi import FastAPI, HTTPException, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import uvicorn
import logging
import os
from contextlib import asynccontextmanager
from dotenv import load_dotenv

# 환경변수 로드 (ai-crawler 루트 디렉토리의 .env 파일)
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))

from app.api.routes import router as api_router, set_crawler_instance
from app.api.websocket import websocket_endpoint
from app.crawlers.multi_engine import MultiEngineCrawler

# 전역 크롤러 인스턴스
crawler_instance = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """애플리케이션 라이프사이클 관리"""
    global crawler_instance
    
    # 시작 시 초기화
    logging.info("🚀 AI Crawler 시스템 초기화 중...")
    crawler_instance = MultiEngineCrawler()
    await crawler_instance.initialize()
    
    # routes에 크롤러 인스턴스 전달
    set_crawler_instance(crawler_instance)
    
    logging.info("✅ 크롤링 엔진 초기화 완료")
    
    yield
    
    # 종료 시 정리
    logging.info("🔄 시스템 종료 중...")
    if crawler_instance:
        await crawler_instance.cleanup()
    logging.info("✅ 시스템 종료 완료")

# FastAPI 앱 생성
app = FastAPI(
    title="AI-Powered Smart Web Crawler",
    description="MCP 기반 지능형 웹 크롤링 시스템",
    version="1.0.0",
    lifespan=lifespan
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API 라우터 등록
app.include_router(api_router, prefix="/api/v1")

# WebSocket 엔드포인트 등록
@app.websocket("/ws/{connection_id}")
async def websocket_route(websocket: WebSocket, connection_id: str):
    await websocket_endpoint(websocket, connection_id)

# 정적 파일 서빙 (결과 파일 다운로드용)
app.mount("/downloads", StaticFiles(directory="results"), name="downloads")

@app.get("/")
async def root():
    """헬스체크 엔드포인트"""
    return {
        "message": "AI-Powered Smart Web Crawler",
        "status": "running",
        "version": "1.0.0"
    }

@app.get("/health")
async def health_check():
    """상세 헬스체크"""
    global crawler_instance
    
    engine_status = {}
    if crawler_instance:
        engine_status = await crawler_instance.get_engine_status()
    
    return {
        "status": "healthy",
        "engines": engine_status,
        "message": "All systems operational"
    }

if __name__ == "__main__":
    # 로깅 설정 - 모든 디버깅 로그 표시
    logging.basicConfig(
        level=logging.DEBUG,  # DEBUG 레벨로 모든 로그 표시
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # 🔧 모든 크롤러 관련 로거를 DEBUG 레벨로 설정
    logging.getLogger("app.crawlers.multi_engine").setLevel(logging.DEBUG)
    logging.getLogger("app.api.routes").setLevel(logging.DEBUG)
    logging.getLogger("app.mcp.tools").setLevel(logging.DEBUG)
    logging.getLogger("app.mcp.client").setLevel(logging.DEBUG)
    
    # 서버 실행
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8001,
        reload=True,
        log_level="debug"  # uvicorn 로그 레벨도 debug로 변경
    ) 