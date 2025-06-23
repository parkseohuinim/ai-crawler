import os
import logging
from typing import Dict, Any
from datetime import datetime
import json
import asyncio

from .base import BaseCrawler, CrawlResult, CrawlStrategy, EngineCapabilities

logger = logging.getLogger(__name__)

try:
    from firecrawl import FirecrawlApp
    FIRECRAWL_AVAILABLE = True
except ImportError:
    FIRECRAWL_AVAILABLE = False
    logger.warning("Firecrawl 라이브러리가 설치되지 않았습니다")

class FirecrawlEngine(BaseCrawler):
    """Firecrawl 기반 크롤링 엔진"""
    
    def __init__(self):
        super().__init__("firecrawl")
        self.client = None
        self.api_key = None
    
    async def initialize(self) -> None:
        """Firecrawl 클라이언트 초기화"""
        if not FIRECRAWL_AVAILABLE:
            raise RuntimeError("Firecrawl 라이브러리가 설치되지 않았습니다")
        
        # API 키 확인
        self.api_key = os.getenv("FIRECRAWL_API_KEY")
        if not self.api_key:
            logger.warning("FIRECRAWL_API_KEY 환경변수가 설정되지 않았습니다")
            # 개발용 더미 키 또는 무료 버전 사용
            self.api_key = "fc-dummy-key-for-development"
        else:
            # API 키 일부만 로깅 (보안상)
            masked_key = self.api_key[:8] + "..." + self.api_key[-4:] if len(self.api_key) > 12 else "***"
            logger.info(f"🔥 Firecrawl API 키 로드됨: {masked_key}")
        
        try:
            self.client = FirecrawlApp(api_key=self.api_key)
            self.is_initialized = True
            logger.info("🔥 Firecrawl 클라이언트 초기화 완료")
        except Exception as e:
            logger.error(f"Firecrawl 초기화 실패: {e}")
            raise
    
    async def cleanup(self) -> None:
        """리소스 정리"""
        self.client = None
        self.is_initialized = False
        logger.info("🔥 Firecrawl 엔진 정리 완료")
    
    def get_capabilities(self) -> Dict[str, Any]:
        """Firecrawl 엔진의 능력"""
        return {
            EngineCapabilities.JAVASCRIPT_RENDERING: True,
            EngineCapabilities.ANTI_BOT_BYPASS: True,
            EngineCapabilities.PREMIUM_SERVICE: True,
            EngineCapabilities.INFINITE_SCROLL: True,
            EngineCapabilities.BULK_PROCESSING: False,  # API 제한으로 인한 단일 처리 권장
            "supported_formats": ["markdown", "html", "text"],
            "rate_limits": "높음 (프리미엄 서비스)",
            "best_for": ["SPA", "안티봇 사이트", "복잡한 JS", "무한스크롤"]
        }
    
    def _extract_hierarchy_from_markdown(self, markdown_text: str, url: str) -> Dict[str, Any]:
        """마크다운 텍스트에서 계층구조 추출"""
        hierarchy = {"depth1": "웹페이지", "depth2": {}, "depth3": {}}
        
        if not markdown_text:
            return hierarchy
        
        lines = markdown_text.split('\n')
        current_h1 = None
        current_h2 = None
        
        for line in lines:
            line = line.strip()
            
            if line.startswith('# ') and not line.startswith('## '):
                # H1 헤더
                current_h1 = line[2:].strip()
                hierarchy["depth1"] = current_h1
                if current_h1 not in hierarchy["depth2"]:
                    hierarchy["depth2"][current_h1] = []
                    
            elif line.startswith('## '):
                # H2 헤더
                current_h2 = line[3:].strip()
                if current_h1:
                    if current_h1 not in hierarchy["depth2"]:
                        hierarchy["depth2"][current_h1] = []
                    hierarchy["depth2"][current_h1].append(current_h2)
                else:
                    hierarchy["depth2"]["기타"] = hierarchy["depth2"].get("기타", [])
                    hierarchy["depth2"]["기타"].append(current_h2)
                    
            elif line.startswith('### '):
                # H3 헤더
                h3_title = line[4:].strip()
                depth3_key = current_h2 or current_h1 or "기타"
                if depth3_key not in hierarchy["depth3"]:
                    hierarchy["depth3"][depth3_key] = []
                hierarchy["depth3"][depth3_key].append(h3_title)
        
        return hierarchy
    
    def _calculate_quality_score(self, result_data: Dict, markdown_text: str) -> float:
        """크롤링 결과 품질 점수 계산"""
        score = 40  # 기본 성공 점수 (Firecrawl이 응답을 반환했으므로)
        
        # 텍스트 길이 점수 (0-30점)
        text_length = len(markdown_text) if markdown_text else 0
        if text_length > 5000:
            score += 30
        elif text_length > 1000:
            score += 20
        elif text_length > 100:
            score += 10
        
        # 구조적 요소 점수 (0-20점)
        if markdown_text:
            structure_score = 0
            if '# ' in markdown_text:
                structure_score += 5
            if '## ' in markdown_text:
                structure_score += 5
            if '- ' in markdown_text or '* ' in markdown_text:
                structure_score += 5
            if '[' in markdown_text and '](' in markdown_text:
                structure_score += 5
            score += structure_score
        
        # 메타데이터 품질 (0-10점)
        if result_data.get("metadata"):
            metadata = result_data["metadata"]
            if metadata.get("title"):
                score += 3
            if metadata.get("description"):
                score += 3
            if metadata.get("keywords"):
                score += 2
            if metadata.get("ogTitle") or metadata.get("ogDescription"):
                score += 2
        
        return min(score, 100.0)
    
    async def crawl(self, url: str, strategy: CrawlStrategy) -> CrawlResult:
        """Firecrawl을 사용한 웹페이지 크롤링"""
        if not self.is_initialized or not self.client:
            raise RuntimeError("Firecrawl 엔진이 초기화되지 않았습니다")
        
        logger.info(f"🔥 Firecrawl로 크롤링 시작: {url}")
        
        try:
            # Firecrawl v1 API 옵션 설정 (2025년 최신 버전)
            scrape_params = {
                "formats": ["markdown", "html"],
                "onlyMainContent": True,  # 메인 콘텐츠만 추출
            }
            
            # 안티봇 모드가 활성화된 경우 추가 옵션
            if strategy.anti_bot_mode:
                scrape_params["waitFor"] = 5000  # 더 오래 대기
            
            # 비동기 처리를 위해 동기 호출을 스레드풀에서 실행
            logger.info(f"🔥 Firecrawl v1 scrape_url 파라미터: {scrape_params}")
            loop = asyncio.get_event_loop()
            
            # Firecrawl v1 API 2025년 버전 - 새로운 ScrapeResponse 객체 사용
            scrape_response = await loop.run_in_executor(
                None, 
                lambda: self.client.scrape_url(url=url, **scrape_params)
            )
            
            # 디버깅을 위한 결과 로깅
            logger.info(f"🔥 Firecrawl 응답 타입: {type(scrape_response)}")
            logger.info(f"🔥 Firecrawl 응답 속성들: {dir(scrape_response) if scrape_response else 'None'}")
            
            if not scrape_response:
                raise Exception("Firecrawl 크롤링 실패: 응답 없음")
            
            # 2025년 최신 SDK - ScrapeResponse 객체에서 직접 속성 접근
            try:
                # success 속성 확인 (있는 경우)
                if hasattr(scrape_response, 'success') and not scrape_response.success:
                    error_msg = getattr(scrape_response, 'error', '알 수 없는 오류')
                    raise Exception(f"Firecrawl 크롤링 실패: {error_msg}")
                
                # data 속성에서 실제 크롤링 결과 추출
                if hasattr(scrape_response, 'data'):
                    result_data = scrape_response.data
                elif hasattr(scrape_response, 'content'):
                    # 직접 content에 접근하는 경우
                    result_data = {
                        'markdown': getattr(scrape_response, 'markdown', ''),
                        'html': getattr(scrape_response, 'html', ''),
                        'metadata': getattr(scrape_response, 'metadata', {})
                    }
                else:
                    # 응답 객체 자체가 데이터인 경우
                    result_data = {
                        'markdown': getattr(scrape_response, 'markdown', ''),
                        'html': getattr(scrape_response, 'html', ''),
                        'metadata': getattr(scrape_response, 'metadata', {})
                    }
                
                logger.info(f"🔥 추출된 데이터 키들: {list(result_data.keys()) if isinstance(result_data, dict) else 'Not a dict'}")
                
                # 마크다운 텍스트 추출
                markdown_text = result_data.get("markdown", result_data.get("content", ""))
                html_content = result_data.get("html", "")
                
                # 메타데이터 추출
                metadata = result_data.get("metadata", {})
                title = metadata.get("title", metadata.get("ogTitle", "제목 없음"))
                
                # 계층구조 추출
                hierarchy = self._extract_hierarchy_from_markdown(markdown_text, url)
                
                # 품질 점수 계산
                quality_score = self._calculate_quality_score(result_data, markdown_text)
                
                # 결과 객체 생성
                crawl_result = CrawlResult(
                    url=url,
                    title=title,
                    text=markdown_text,
                    hierarchy=hierarchy,
                    metadata={
                        "crawler_used": "firecrawl",
                        "processing_time": f"{strategy.timeout}s",
                        "content_quality": "high" if quality_score > 80 else "medium" if quality_score > 50 else "low",
                        "extraction_confidence": quality_score / 100,
                        "firecrawl_metadata": metadata,
                        "html_length": len(html_content),
                        "markdown_length": len(markdown_text),
                        "quality_score": quality_score
                    },
                    status="complete",
                    timestamp=datetime.now()
                )
                
                logger.info(f"✅ Firecrawl 크롤링 성공: {url} (품질: {quality_score:.1f}/100)")
                return crawl_result
                
            except AttributeError as e:
                logger.error(f"🔥 Firecrawl 응답 객체 속성 접근 오류: {e}")
                # 응답 객체의 실제 구조를 확인하기 위한 추가 로깅
                logger.error(f"🔥 응답 객체 타입: {type(scrape_response)}")
                logger.error(f"🔥 응답 객체 내용: {scrape_response}")
                raise Exception(f"Firecrawl 응답 처리 실패: {e}")
            
        except Exception as e:
            logger.error(f"❌ Firecrawl 크롤링 실패: {url} - {e}")
            return CrawlResult(
                url=url,
                title="",
                text="",
                hierarchy={},
                metadata={
                    "crawler_used": "firecrawl",
                    "error_type": type(e).__name__,
                    "processing_time": "0s"
                },
                status="failed",
                timestamp=datetime.now(),
                error=str(e)
            ) 