from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl
import uvicorn
from typing import Optional, Dict, Any
import logging

from core.accessibility_checker import AccessibilityChecker
from models.report_models import CheckResult, CheckRequest

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="웹 접근성 검사 API",
    description="웹사이트의 접근성을 종합적으로 검사하는 API",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

checker = AccessibilityChecker()

@app.get("/")
async def root():
    return {"message": "웹 접근성 검사 API 서버가 실행 중입니다."}

@app.post("/check", response_model=CheckResult)
async def check_accessibility(request: CheckRequest):
    """웹사이트 접근성 검사를 수행합니다."""
    try:
        logger.info(f"접근성 검사 시작: {request.url}")
        result = await checker.check_website(request.url, request.options)
        logger.info(f"접근성 검사 완료: {request.url}")
        return result
    except Exception as e:
        logger.error(f"접근성 검사 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=f"검사 중 오류가 발생했습니다: {str(e)}")

@app.get("/health")
async def health_check():
    """서버 상태를 확인합니다."""
    return {"status": "healthy"}

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        log_level="info"
    )