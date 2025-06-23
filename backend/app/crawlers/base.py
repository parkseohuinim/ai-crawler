from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime
import asyncio
import logging

logger = logging.getLogger(__name__)

@dataclass
class CrawlResult:
    """크롤링 결과 표준 데이터 클래스"""
    url: str
    title: str
    text: str
    hierarchy: Dict[str, Any]
    metadata: Dict[str, Any]
    status: str
    timestamp: datetime
    error: Optional[str] = None

@dataclass
class CrawlStrategy:
    """크롤링 전략 설정"""
    engine_priority: List[str]
    timeout: int = 30  # 초기 연결 타임아웃
    max_retries: int = 3
    wait_time: float = 1.0
    extract_images: bool = False
    extract_links: bool = True
    custom_selectors: Dict[str, str] = None
    anti_bot_mode: bool = False
    # 활동 기반 타임아웃 설정
    activity_timeout: int = 15  # 마지막 활동으로부터 15초 후 타임아웃
    max_total_time: int = 300   # 최대 총 시간 5분 (안전장치)
    
    def __post_init__(self):
        if self.custom_selectors is None:
            self.custom_selectors = {}

class BaseCrawler(ABC):
    """크롤링 엔진 베이스 클래스"""
    
    def __init__(self, name: str):
        self.name = name
        self.is_initialized = False
        self.stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "avg_response_time": 0.0
        }
    
    @abstractmethod
    async def initialize(self) -> None:
        """엔진 초기화 (API 키 설정, 브라우저 시작 등)"""
        pass
    
    @abstractmethod
    async def crawl(self, url: str, strategy: CrawlStrategy) -> CrawlResult:
        """웹페이지 크롤링 실행"""
        pass
    
    @abstractmethod
    async def cleanup(self) -> None:
        """리소스 정리 (브라우저 종료, 연결 닫기 등)"""
        pass
    
    @abstractmethod
    def get_capabilities(self) -> Dict[str, Any]:
        """엔진의 능력과 특성 반환"""
        pass
    
    async def health_check(self) -> Dict[str, Any]:
        """엔진 상태 확인"""
        return {
            "name": self.name,
            "initialized": self.is_initialized,
            "stats": self.stats,
            "capabilities": self.get_capabilities()
        }
    
    def _update_stats(self, success: bool, response_time: float):
        """통계 업데이트"""
        self.stats["total_requests"] += 1
        if success:
            self.stats["successful_requests"] += 1
        else:
            self.stats["failed_requests"] += 1
        
        # 평균 응답 시간 계산
        total = self.stats["total_requests"]
        current_avg = self.stats["avg_response_time"]
        self.stats["avg_response_time"] = ((current_avg * (total - 1)) + response_time) / total
    
    async def crawl_with_retry(self, url: str, strategy: CrawlStrategy) -> CrawlResult:
        """재시도 로직이 포함된 크롤링"""
        last_error = None
        
        for attempt in range(strategy.max_retries):
            try:
                start_time = asyncio.get_event_loop().time()
                result = await self.crawl(url, strategy)
                end_time = asyncio.get_event_loop().time()
                
                self._update_stats(True, end_time - start_time)
                return result
                
            except Exception as e:
                last_error = e
                error_msg = str(e).lower()
                
                # 재시도하지 않을 에러 유형들
                permanent_errors = [
                    "404", "not found",  # HTTP 404
                    "403", "forbidden",  # 접근 금지
                    "dns", "name resolution failed",  # DNS 오류
                    "connection refused",  # 연결 거부
                    "invalid url", "malformed url",  # 잘못된 URL
                    "ssl certificate", "certificate verify failed"  # SSL 인증서 오류
                ]
                
                # 영구적 에러인지 확인
                is_permanent = any(err in error_msg for err in permanent_errors)
                
                if is_permanent:
                    logger.warning(f"🚫 영구적 에러 감지, 재시도 건너뜀: {type(e).__name__}: {e}")
                    break
                
                if attempt < strategy.max_retries - 1:
                    wait_time = strategy.wait_time * (2 ** attempt)  # 지수 백오프
                    logger.info(f"🔄 재시도 {attempt + 2}/{strategy.max_retries} ({wait_time:.1f}초 후): {type(e).__name__}")
                    await asyncio.sleep(wait_time)
                    continue
        
        # 모든 재시도 실패
        self._update_stats(False, 0)
        return CrawlResult(
            url=url,
            title="",
            text="",
            hierarchy={},
            metadata={"crawler_used": self.name, "error": str(last_error)},
            status="failed",
            timestamp=datetime.now(),
            error=str(last_error)
        )

class EngineCapabilities:
    """엔진 능력 상수"""
    JAVASCRIPT_RENDERING = "javascript_rendering"
    ANTI_BOT_BYPASS = "anti_bot_bypass"
    BULK_PROCESSING = "bulk_processing"
    AI_EXTRACTION = "ai_extraction"
    FAST_STATIC = "fast_static"
    PREMIUM_SERVICE = "premium_service"
    INFINITE_SCROLL = "infinite_scroll"
    LOGIN_SUPPORT = "login_support" 