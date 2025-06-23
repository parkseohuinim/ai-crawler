import os
import logging
from typing import Dict, Any, Optional
from datetime import datetime
import json
import asyncio

from .base import BaseCrawler, CrawlResult, CrawlStrategy, EngineCapabilities

logger = logging.getLogger(__name__)

try:
    from crawl4ai import AsyncWebCrawler
    from crawl4ai.extraction_strategy import LLMExtractionStrategy, CosineStrategy
    from crawl4ai.chunking_strategy import RegexChunking
    CRAWL4AI_AVAILABLE = True
except ImportError:
    CRAWL4AI_AVAILABLE = False
    logger.warning("Crawl4AI 라이브러리가 설치되지 않았습니다")

class Crawl4AIEngine(BaseCrawler):
    """Crawl4AI 기반 크롤링 엔진 - AI 기반 스마트 콘텐츠 추출"""
    
    def __init__(self):
        super().__init__("crawl4ai")
        self.crawler = None
        self.openai_api_key = None
    
    async def initialize(self) -> None:
        """Crawl4AI 크롤러 초기화"""
        if not CRAWL4AI_AVAILABLE:
            raise RuntimeError("Crawl4AI 라이브러리가 설치되지 않았습니다")
        
        # OpenAI API 키 확인 (LLM 추출용)
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        if not self.openai_api_key:
            logger.warning("OPENAI_API_KEY가 설정되지 않았습니다. 기본 추출 전략을 사용합니다.")
        else:
            # API 키 일부만 로깅 (보안상)
            masked_key = self.openai_api_key[:8] + "..." + self.openai_api_key[-4:] if len(self.openai_api_key) > 12 else "***"
            logger.info(f"🤖 OpenAI API 키 로드됨: {masked_key}")
        
        try:
            # Crawl4AI 비동기 크롤러 초기화 (최신 버전 API 사용)
            self.crawler = AsyncWebCrawler(
                verbose=True,
                headless=True
            )
            
            # 크롤러 시작 (astart 대신 start 사용)
            await self.crawler.start()
            self.is_initialized = True
            logger.info("🤖 Crawl4AI 엔진 초기화 완료")
            
        except Exception as e:
            logger.error(f"Crawl4AI 초기화 실패: {e}")
            raise
    
    async def cleanup(self) -> None:
        """리소스 정리"""
        if self.crawler:
            try:
                # aclose 대신 close 사용
                await self.crawler.close()
                logger.info("🤖 Crawl4AI 크롤러 종료 완료")
            except Exception as e:
                logger.error(f"Crawl4AI 크롤러 종료 중 오류: {e}")
            finally:
                self.crawler = None
        
        self.is_initialized = False
        logger.info("🤖 Crawl4AI 엔진 정리 완료")
    
    def get_capabilities(self) -> Dict[str, Any]:
        """Crawl4AI 엔진의 능력"""
        return {
            EngineCapabilities.JAVASCRIPT_RENDERING: True,
            EngineCapabilities.ANTI_BOT_BYPASS: True,
            EngineCapabilities.PREMIUM_SERVICE: False,  # 오픈소스
            EngineCapabilities.INFINITE_SCROLL: True,
            EngineCapabilities.BULK_PROCESSING: True,
            "supported_formats": ["markdown", "html", "structured_data"],
            "ai_features": ["llm_extraction", "semantic_chunking", "smart_filtering"],
            "rate_limits": "브라우저 기반 (무제한)",
            "best_for": ["LLM 통합", "구조화된 데이터", "AI 기반 추출", "복잡한 SPA"]
        }
    
    def _create_extraction_strategy(self, strategy: CrawlStrategy) -> Optional[Any]:
        """추출 전략 생성 (현재 비활성화 - deprecated 에러 방지)"""
        # OpenAI API 키가 없거나 LLM 전략에서 에러가 발생하므로 비활성화
        logger.info("💡 LLM 추출 전략 비활성화 (기본 추출 사용)")
        return None
        
        # 원래 코드는 주석 처리
        """
        if not self.openai_api_key:
            return None
        
        try:
            from crawl4ai.models import LLMConfig
            
            # LLM 설정 생성 (최신 API)
            llm_config = LLMConfig(
                provider="openai/gpt-4o-mini",  # 비용 효율적인 모델
                api_token=self.openai_api_key
            )
            
            # LLM 기반 추출 전략 생성
            llm_strategy = LLMExtractionStrategy(
                llm_config=llm_config,
                instruction="주요 콘텐츠를 마크다운 형식으로 추출하세요.",
                extraction_type="block",
                apply_chunking=True,
                chunking_strategy=RegexChunking()
            )
            return llm_strategy
        except Exception as e:
            logger.error(f"LLM 추출 전략 생성 실패: {e}")
            return None
        """
    
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
        score = 50  # Crawl4AI 기본 점수 (AI 기반)
        
        # 텍스트 길이 점수 (0-25점)
        text_length = len(markdown_text) if markdown_text else 0
        if text_length > 8000:
            score += 25
        elif text_length > 3000:
            score += 20
        elif text_length > 1000:
            score += 15
        elif text_length > 100:
            score += 10
        
        # 구조적 요소 점수 (0-15점)
        if markdown_text:
            structure_score = 0
            if '# ' in markdown_text:
                structure_score += 4
            if '## ' in markdown_text:
                structure_score += 4
            if '- ' in markdown_text or '* ' in markdown_text:
                structure_score += 3
            if '[' in markdown_text and '](' in markdown_text:
                structure_score += 4
            score += structure_score
        
        # AI 추출 사용 보너스 (0-10점)
        if result_data.get("extracted_content"):
            score += 10
        elif result_data.get("llm_extraction_strategy"):
            score += 5
        
        return min(score, 100.0)
    
    async def crawl(self, url: str, strategy: CrawlStrategy) -> CrawlResult:
        """Crawl4AI를 사용한 웹페이지 크롤링"""
        if not self.is_initialized or not self.crawler:
            raise RuntimeError("Crawl4AI 엔진이 초기화되지 않았습니다")
        
        logger.info(f"🤖 Crawl4AI로 크롤링 시작: {url}")
        
        try:
            # 추출 전략 생성
            extraction_strategy = self._create_extraction_strategy(strategy)
            
            # Crawl4AI 크롤링 옵션
            crawl_options = {
                "word_count_threshold": 10,  # 최소 단어 수
                "only_text": False,  # HTML도 함께 반환
                "bypass_cache": True,  # 캐시 우회
                "remove_overlay_elements": True,  # 오버레이 제거
                "simulate_user": True,  # 사용자 시뮬레이션
            }
            
            # CSS 선택자 설정 - Google 같은 사이트를 위해 더 포괄적으로 설정
            css_selector = ""  # 전체 페이지 크롤링 (제한 없음)
            
            # 🔧 Google 같은 JavaScript 의존 사이트 감지
            is_js_heavy_site = any(domain in url.lower() for domain in [
                'google.com', 'gmail.com', 'youtube.com', 
                'facebook.com', 'twitter.com', 'instagram.com',
                'linkedin.com', 'reddit.com'
            ])
            
            # 대기 조건 설정 - JavaScript 의존 사이트는 더 오래 대기
            if is_js_heavy_site:
                wait_for = "networkidle"  # 네트워크 활동이 멈출 때까지 대기
                crawl_options["delay_before_return_html"] = 5  # 5초 추가 대기
                crawl_options["simulate_user"] = True
                crawl_options["override_navigator"] = True
                logger.info(f"🤖 JavaScript 의존 사이트 감지: {url} - 확장된 대기 설정 적용")
            else:
                wait_for = "domcontentloaded"
                crawl_options["delay_before_return_html"] = 2  # 기본 2초 대기
            
            if strategy.anti_bot_mode:
                wait_for = "networkidle"
                crawl_options["simulate_user"] = True
                crawl_options["override_navigator"] = True
            
            # LLM 추출 전략 사용 여부
            if extraction_strategy:
                crawl_options["extraction_strategy"] = extraction_strategy
                logger.info("🤖 LLM 추출 전략 활성화")
            
            # 크롤링 실행
            logger.info(f"🤖 Crawl4AI 옵션: {crawl_options}")
            result = await self.crawler.arun(
                url=url,
                css_selector=css_selector,
                wait_for=wait_for,
                **crawl_options
            )
            
            # 결과 처리
            if not result.success:
                error_msg = f"크롤링 실패: {result.error_message or '알 수 없는 오류'}"
                raise Exception(error_msg)
            
            # 마크다운 텍스트 추출
            markdown_text = result.markdown or result.cleaned_html or ""
            html_content = result.html or ""
            
            # 메타데이터 추출
            metadata = {
                "title": result.metadata.get("title", "제목 없음") if result.metadata else "제목 없음",
                "description": result.metadata.get("description", "") if result.metadata else "",
                "keywords": result.metadata.get("keywords", "") if result.metadata else "",
            }
            
            # 추출된 콘텐츠 확인
            extracted_content = None
            if hasattr(result, 'extracted_content') and result.extracted_content:
                extracted_content = result.extracted_content
                logger.info("🤖 LLM 추출 콘텐츠 감지됨")
            
            # 계층구조 추출
            hierarchy = self._extract_hierarchy_from_markdown(markdown_text, url)
            
            # 품질 점수 계산
            result_data = {
                "extracted_content": extracted_content,
                "llm_extraction_strategy": extraction_strategy is not None,
                "metadata": metadata
            }
            quality_score = self._calculate_quality_score(result_data, markdown_text)
            
            # 결과 객체 생성
            crawl_result = CrawlResult(
                url=url,
                title=metadata["title"],
                text=markdown_text,
                hierarchy=hierarchy,
                metadata={
                    "crawler_used": "crawl4ai",
                    "processing_time": f"{strategy.timeout}s",
                    "content_quality": "high" if quality_score > 85 else "medium" if quality_score > 60 else "low",
                    "extraction_confidence": quality_score / 100,
                    "crawl4ai_metadata": metadata,
                    "html_length": len(html_content),
                    "markdown_length": len(markdown_text),
                    "quality_score": quality_score,
                    "ai_extraction_used": extraction_strategy is not None,
                    "extracted_content_available": extracted_content is not None,
                    "success": result.success,
                    "crawl4ai_screenshot": result.screenshot if hasattr(result, 'screenshot') else None
                },
                status="complete",
                timestamp=datetime.now()
            )
            
            logger.info(f"✅ Crawl4AI 크롤링 성공: {url} (품질: {quality_score:.1f}/100)")
            return crawl_result
            
        except Exception as e:
            logger.error(f"❌ Crawl4AI 크롤링 실패: {url} - {e}")
            return CrawlResult(
                url=url,
                title="",
                text="",
                hierarchy={},
                metadata={
                    "crawler_used": "crawl4ai",
                    "error_type": type(e).__name__,
                    "processing_time": "0s"
                },
                status="failed",
                timestamp=datetime.now(),
                error=str(e)
            ) 