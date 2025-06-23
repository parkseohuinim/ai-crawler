import logging
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime
from urllib.parse import urlparse
import re

from .base import BaseCrawler, CrawlResult, CrawlStrategy
from .firecrawl_engine import FirecrawlEngine
from .requests_engine import RequestsEngine
from .crawl4ai_engine import Crawl4AIEngine
from .playwright_engine import PlaywrightEngine

# MCP 클라이언트 통합
from ..mcp import MCPClient, MCPToolsManager, CrawlingStrategyManager

logger = logging.getLogger(__name__)

class MultiEngineCrawler:
    """다중 크롤링 엔진 통합 관리자 (MCP 기반 AI 분석 통합)"""
    
    def __init__(self):
        self.engines: Dict[str, BaseCrawler] = {}
        self.is_initialized = False
        
        # MCP 클라이언트 및 관리자들
        self.mcp_client = MCPClient()
        self.mcp_tools_manager = None
        self.strategy_manager = None
        
        # 크롤링 전략 설정 (사이트 유형별) - Phase 2 업데이트
        self.crawler_strategies = {
            "complex_spa": {
                "primary": "crawl4ai",  # AI 기반 SPA 크롤링
                "fallback": ["firecrawl", "playwright", "requests"],
                "characteristics": ["React/Vue", "무한스크롤", "복잡한 JS"]
            },
            "ai_analysis_needed": {
                "primary": "crawl4ai",  # LLM 추출 전략 사용
                "fallback": ["firecrawl", "playwright", "requests"],
                "characteristics": ["복잡한 구조", "의미적 추출", "AI 분류 필요"]
            },
            "anti_bot_heavy": {
                "primary": "playwright",  # 브라우저 기반 우회
                "fallback": ["firecrawl", "crawl4ai", "requests"],
                "characteristics": ["Cloudflare", "reCAPTCHA", "강한 봇 차단"]
            },
            "standard_dynamic": {
                "primary": "playwright",  # 브라우저 자동화
                "fallback": ["crawl4ai", "firecrawl", "requests"],
                "characteristics": ["표준 동적사이트", "로그인 필요", "세밀한 제어"]
            },
            "simple_static": {
                "primary": "requests",  # 빠른 처리
                "fallback": ["crawl4ai", "firecrawl", "playwright"],
                "characteristics": ["정적 HTML", "빠른 처리", "단순 구조"]
            }
        }
    
    async def initialize(self):
        """모든 크롤링 엔진 및 MCP 클라이언트 초기화"""
        logger.info("🔧 크롤링 엔진들 및 MCP 클라이언트 초기화 시작...")
        
        # 사용 가능한 엔진들 등록 (Phase 2 - 모든 엔진 활성화)
        self.engines = {
            "requests": RequestsEngine(),        # 기본 HTTP 크롤러
            "firecrawl": FirecrawlEngine(),      # 프리미엄 서비스
            "crawl4ai": Crawl4AIEngine(),        # AI 기반 크롤러
            "playwright": PlaywrightEngine(),    # 브라우저 자동화
        }
        
        # 각 엔진 초기화
        failed_engines = []
        for name, engine in self.engines.items():
            try:
                await engine.initialize()
                logger.info(f"✅ {name} 엔진 초기화 완료")
            except Exception as e:
                logger.error(f"❌ {name} 엔진 초기화 실패: {e}")
                # 실패한 엔진을 별도 리스트에 기록
                failed_engines.append(name)
        
        # 실패한 엔진들을 딕셔너리에서 제거
        for name in failed_engines:
            del self.engines[name]
        
        # MCP 관리자들 초기화
        self.mcp_tools_manager = MCPToolsManager(self.mcp_client)
        self.strategy_manager = CrawlingStrategyManager(self.mcp_client)
        
        self.is_initialized = True
        logger.info(f"🚀 총 {len(self.engines)}개 엔진 + MCP 클라이언트 초기화 완료")
    
    async def cleanup(self):
        """모든 엔진 정리"""
        logger.info("🔄 크롤링 엔진 정리 시작...")
        
        for name, engine in self.engines.items():
            try:
                await engine.cleanup()
                logger.info(f"✅ {name} 엔진 정리 완료")
            except Exception as e:
                logger.error(f"❌ {name} 엔진 정리 실패: {e}")
        
        self.is_initialized = False
        logger.info("🏁 모든 엔진 정리 완료")
    
    def _validate_url(self, url: str) -> tuple[bool, str]:
        """URL 유효성 검사"""
        try:
            # 기본 URL 형식 검사
            if not url or not isinstance(url, str):
                return False, "URL이 비어있거나 문자열이 아닙니다"
            
            # URL 파싱
            parsed = urlparse(url.strip())
            
            # 스키마 검사
            if not parsed.scheme or parsed.scheme.lower() not in ['http', 'https']:
                return False, f"지원하지 않는 스키마: {parsed.scheme}"
            
            # 도메인 검사
            if not parsed.netloc:
                return False, "도메인이 없습니다"
            
            # 도메인 형식 검사 (기본적인 패턴)
            domain_pattern = r'^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*$'
            if not re.match(domain_pattern, parsed.netloc.split(':')[0]):
                return False, f"잘못된 도메인 형식: {parsed.netloc}"
            
            # 알려진 문제 URL 패턴들
            known_issues = [
                'lineCombOrder/lineCombList.do',  # 404를 반환하는 것으로 알려진 패턴
                'javascript:',  # JavaScript 스키마
                'mailto:',  # 이메일 링크
                '#',  # 앵커만 있는 링크
            ]
            
            for issue in known_issues:
                if issue in url:
                    return False, f"알려진 문제 URL 패턴: {issue}"
            
            return True, "유효한 URL"
            
        except Exception as e:
            return False, f"URL 검증 중 오류: {str(e)}"
    
    async def analyze_site_and_get_strategy(self, url: str, sample_html: str = "") -> Dict[str, Any]:
        """MCP 기반 사이트 분석 후 크롤링 전략 생성"""
        logger.info(f"🧠 MCP 기반 사이트 분석 시작: {url}")
        
        # 🔧 디버깅: MCP 도구 매니저 상태 확인
        logger.info(f"🔧 DEBUG: MCP 도구 매니저 초기화 상태: {self.mcp_tools_manager is not None}")
        logger.info(f"🔧 DEBUG: MCP 클라이언트 초기화 상태: {self.mcp_client is not None}")
        print(f"[DEBUG] MCP 도구 매니저 초기화 상태: {self.mcp_tools_manager is not None}")
        print(f"[DEBUG] MCP 클라이언트 초기화 상태: {self.mcp_client is not None}")
        
        try:
            # 🔧 디버깅: MCP 연결 시도
            logger.info("🔧 DEBUG: MCP 클라이언트 연결 시도 중...")
            print(f"[DEBUG] MCP 클라이언트 연결 시도 중...")
            
            # MCP 클라이언트로 연결하여 분석 실행
            async with self.mcp_client.connect():
                logger.info("🔧 DEBUG: MCP 클라이언트 연결 성공")
                print(f"[DEBUG] MCP 클라이언트 연결 성공")
                
                # 🔧 디버깅: 종합 분석 실행 전
                logger.info(f"🔧 DEBUG: analyze_website_completely 호출 시작 - URL: {url}, HTML 길이: {len(sample_html)}")
                
                # 종합 분석 실행 (사이트 분석 → 구조 감지 → 전략 생성)
                complete_analysis = await self.mcp_tools_manager.analyze_website_completely(url, sample_html)
                
                # 🔧 디버깅: 분석 결과 상세 로그
                logger.info(f"🔧 DEBUG: analyze_website_completely 완료")
                logger.info(f"🔧 DEBUG: 분석 결과 타입: {type(complete_analysis)}")
                logger.info(f"🔧 DEBUG: 분석 결과 키들: {list(complete_analysis.keys()) if isinstance(complete_analysis, dict) else 'Not a dict'}")
                
                if "error" in complete_analysis:
                    logger.warning(f"🔧 DEBUG: MCP 분석에서 에러 감지: {complete_analysis['error']}")
                    logger.warning(f"MCP 분석 실패, 폴백 전략 사용: {complete_analysis['error']}")
                    fallback_result = self._get_fallback_strategy(url)
                    logger.info(f"🔧 DEBUG: 폴백 전략 결과: {fallback_result}")
                    return fallback_result
                
                # 🔧 디버깅: 성공적인 MCP 분석 결과 상세 로그
                logger.info(f"🔧 DEBUG: MCP 분석 성공!")
                print(f"[DEBUG] MCP 분석 성공!")
                if "crawling_strategy" in complete_analysis:
                    strategy = complete_analysis["crawling_strategy"]
                    logger.info(f"🔧 DEBUG: 추천 엔진: {strategy.get('recommended_engine', 'None')}")
                    logger.info(f"🔧 DEBUG: 폴백 엔진들: {strategy.get('fallback_engines', [])}")
                    print(f"[DEBUG] 추천 엔진: {strategy.get('recommended_engine', 'None')}, 폴백 엔진들: {strategy.get('fallback_engines', [])}")
                else:
                    logger.warning(f"🔧 DEBUG: crawling_strategy 키가 없음! 전체 결과: {complete_analysis}")
                    print(f"[DEBUG] crawling_strategy 키가 없음! 전체 결과: {complete_analysis}")
                
                logger.info(f"✅ MCP 기반 분석 완료: {url}")
                return complete_analysis
                
        except Exception as e:
            # 🔧 디버깅: 예외 상세 정보
            logger.error(f"🔧 DEBUG: MCP 분석 중 예외 발생!")
            logger.error(f"🔧 DEBUG: 예외 타입: {type(e).__name__}")
            logger.error(f"🔧 DEBUG: 예외 메시지: {str(e)}")
            logger.error(f"🔧 DEBUG: 예외 상세: {repr(e)}")
            print(f"[DEBUG] MCP 분석 중 예외 발생! 타입: {type(e).__name__}, 메시지: {str(e)}")
            
            logger.error(f"MCP 분석 중 오류: {e}")
            fallback_result = self._get_fallback_strategy(url)
            logger.info(f"🔧 DEBUG: 예외 후 폴백 전략 결과: {fallback_result}")
            print(f"[DEBUG] 예외 후 폴백 전략 사용")
            return fallback_result
    
    def _get_fallback_strategy(self, url: str) -> Dict[str, Any]:
        """MCP 실패 시 사용할 폴백 전략 (개선된 휴리스틱 기반)"""
        domain = url.lower()
        
        logger.warning(f"⚠️ MCP 분석 실패 - 폴백 전략 사용: {url}")
        
        # 🔧 디버깅: 도메인 분석 과정
        logger.info(f"🔧 DEBUG: 폴백 전략 - 도메인 분석: {domain}")
        print(f"[DEBUG] 폴백 전략 - 도메인 분석: {domain}")
        
        # 개선된 패턴 매칭
        strategy_type = None
        
        # 🔧 디버깅: 각 패턴 매칭 과정
        spa_keywords = ['react.dev', 'vue', 'angular', 'spa']
        shopping_keywords = ['shop.kt.com', 'shopping', 'ecommerce', 'store']
        security_keywords = ['cloudflare', 'protected', 'secure']
        dynamic_keywords = ['dynamic', 'app', 'portal']
        
        logger.info(f"🔧 DEBUG: SPA 키워드 체크: {spa_keywords}")
        print(f"[DEBUG] SPA 키워드 체크: {spa_keywords}")
        if any(keyword in domain for keyword in spa_keywords):
            strategy_type = "complex_spa"
            logger.info(f"🎯 폴백 전략: SPA 사이트로 판단 → {strategy_type}")
            print(f"[DEBUG] SPA 사이트로 판단 → {strategy_type}")
        else:
            logger.info(f"🔧 DEBUG: SPA 키워드 매칭 실패")
            print(f"[DEBUG] SPA 키워드 매칭 실패")
        
        if not strategy_type:
            logger.info(f"🔧 DEBUG: 쇼핑몰 키워드 체크: {shopping_keywords}")
            if any(keyword in domain for keyword in shopping_keywords):
                strategy_type = "ai_analysis_needed"  # crawl4ai 우선
                logger.info(f"🎯 폴백 전략: 쇼핑몰/AI 필요 사이트 → {strategy_type}")
            else:
                logger.info(f"🔧 DEBUG: 쇼핑몰 키워드 매칭 실패")
        
        if not strategy_type:
            logger.info(f"🔧 DEBUG: 보안 키워드 체크: {security_keywords}")
            if any(keyword in domain for keyword in security_keywords):
                strategy_type = "anti_bot_heavy"
                logger.info(f"🎯 폴백 전략: 봇 차단 사이트 → {strategy_type}")
            else:
                logger.info(f"🔧 DEBUG: 보안 키워드 매칭 실패")
        
        if not strategy_type:
            logger.info(f"🔧 DEBUG: 동적 키워드 체크: {dynamic_keywords}")
            if any(keyword in domain for keyword in dynamic_keywords):
                strategy_type = "standard_dynamic"
                logger.info(f"🎯 폴백 전략: 동적 사이트 → {strategy_type}")
            else:
                logger.info(f"🔧 DEBUG: 동적 키워드 매칭 실패")
        
        if not strategy_type:
            strategy_type = "simple_static"
            logger.info(f"🎯 폴백 전략: 단순 정적 사이트 → {strategy_type} (기본값)")
        
        # 🔧 디버깅: 선택된 전략 정보
        logger.info(f"🔧 DEBUG: 최종 선택된 전략 타입: {strategy_type}")
        
        if strategy_type not in self.crawler_strategies:
            logger.error(f"🔧 DEBUG: 전략 타입 '{strategy_type}'이 crawler_strategies에 없음!")
            logger.error(f"🔧 DEBUG: 사용 가능한 전략들: {list(self.crawler_strategies.keys())}")
            strategy_type = "simple_static"  # 안전한 기본값
        
        config = self.crawler_strategies[strategy_type]
        
        # 🔧 디버깅: 전략 설정 정보
        logger.info(f"🔧 DEBUG: 전략 설정:")
        logger.info(f"   - primary: {config['primary']}")
        logger.info(f"   - fallback: {config['fallback']}")
        logger.info(f"   - characteristics: {config.get('characteristics', [])}")
        
        result = {
            "url": url,
            "crawling_strategy": {
                "recommended_engine": config["primary"],
                "fallback_engines": config["fallback"],
                "strategy_type": strategy_type
            },
            "is_fallback": True,
            "status": "fallback_strategy"
        }
        
        # 🔧 디버깅: 최종 결과
        logger.info(f"🔧 DEBUG: 폴백 전략 최종 결과:")
        logger.info(f"   - recommended_engine: {result['crawling_strategy']['recommended_engine']}")
        logger.info(f"   - fallback_engines: {result['crawling_strategy']['fallback_engines']}")
        logger.info(f"   - strategy_type: {result['crawling_strategy']['strategy_type']}")
        print(f"[DEBUG] 폴백 전략 최종 결과: 추천={result['crawling_strategy']['recommended_engine']}, 폴백={result['crawling_strategy']['fallback_engines']}, 타입={result['crawling_strategy']['strategy_type']}")
        
        return result
    
    def get_strategy_config(self, strategy_type: str) -> CrawlStrategy:
        """전략 타입에 따른 크롤링 설정 반환"""
        if strategy_type not in self.crawler_strategies:
            strategy_type = "simple_static"
        
        config = self.crawler_strategies[strategy_type]
        
        # 사용 가능한 엔진만 필터링
        available_engines = [eng for eng in [config["primary"]] + config["fallback"] 
                           if eng in self.engines]
        
        if not available_engines:
            available_engines = list(self.engines.keys())
        
        # 전략 타입에 따른 동적 타임아웃 설정
        timeout_config = {
            "complex_spa": 60,  # SPA는 로딩 시간이 길어서 60초
            "ai_analysis_needed": 45,  # AI 분석 필요 사이트는 45초
            "anti_bot_heavy": 60,  # 봇 차단 사이트는 우회 시간 필요해서 60초
            "standard_dynamic": 40,  # 표준 동적 사이트는 40초
            "simple_static": 30  # 정적 사이트는 30초
        }
        
        return CrawlStrategy(
            engine_priority=available_engines,
            timeout=timeout_config.get(strategy_type, 30),
            max_retries=3,
            wait_time=1.0
        )
    
    async def crawl_with_strategy(self, url: str, custom_strategy: Optional[CrawlStrategy] = None) -> CrawlResult:
        """MCP 기반 지능형 크롤링"""
        if not self.is_initialized:
            raise RuntimeError("크롤러가 초기화되지 않았습니다")
        
        # 🔧 디버깅: 현재 사용 가능한 엔진들 출력
        logger.info(f"🔧 DEBUG: 현재 초기화된 엔진들: {list(self.engines.keys())}")
        print(f"[DEBUG] 현재 초기화된 엔진들: {list(self.engines.keys())}")
        
        # URL 유효성 검사
        is_valid, validation_msg = self._validate_url(url)
        if not is_valid:
            logger.error(f"🚫 유효하지 않은 URL: {url} - {validation_msg}")
            return CrawlResult(
                url=url,
                title="",
                text="",
                hierarchy={},
                metadata={"error": validation_msg, "validation_failed": True},
                status="failed",
                timestamp=datetime.now(),
                error=f"URL 유효성 검사 실패: {validation_msg}"
            )
        
        logger.info(f"🔍 MCP 기반 사이트 분석 시작: {url}")
        print(f"[DEBUG] 🔍 MCP 기반 사이트 분석 시작: {url}")
        
        # MCP 분석 결과
        analysis_result = None
        
        # 전략 결정
        if custom_strategy:
            strategy = custom_strategy
            logger.info("👤 사용자 정의 전략 사용")
            logger.info(f"🔧 DEBUG: 사용자 정의 전략 엔진들: {strategy.engine_priority}")
            print(f"[DEBUG] 👤 사용자 정의 전략 사용: {strategy.engine_priority}")
        else:
            # MCP 기반 종합 분석 실행
            logger.info(f"🔍 MCP 분석 시작 for {url}")
            print(f"[DEBUG] 🔍 MCP 분석 시작 for {url}")
            analysis_result = await self.analyze_site_and_get_strategy(url)
            logger.info(f"🔍 MCP 분석 완료 - 결과 타입: {type(analysis_result)}")
            logger.debug(f"🔍 MCP 분석 결과 키들: {list(analysis_result.keys()) if isinstance(analysis_result, dict) else 'Not a dict'}")
            print(f"[DEBUG] 🔍 MCP 분석 완료 - 결과 타입: {type(analysis_result)}")
            
            # 🔧 디버깅: MCP 분석 결과 전체 출력
            logger.info(f"🔧 DEBUG: MCP 분석 결과 전체: {analysis_result}")
            print(f"[DEBUG] 🔧 MCP 분석 결과 전체: {analysis_result}")
            
            # 폴백 전략 확인
            if analysis_result.get("is_fallback"):
                logger.warning(f"⚠️ 폴백 전략 감지! 폴백 이유: {analysis_result.get('status', 'Unknown')}")
                print(f"[DEBUG] ⚠️ 폴백 전략 감지! 폴백 이유: {analysis_result.get('status', 'Unknown')}")
            else:
                print(f"[DEBUG] ✅ MCP 분석 성공 (폴백 아님)")
            
            # 분석 결과에서 전략 추출
            crawling_strategy = analysis_result.get("crawling_strategy", {})
            recommended_crawler = crawling_strategy.get("recommended_engine", "requests")
            fallback_crawlers = crawling_strategy.get("fallback_engines", ["requests"])
            
            # 🔧 디버깅: 전략 추출 결과
            logger.info(f"🔧 DEBUG: 추출된 전략 정보:")
            logger.info(f"   - crawling_strategy: {crawling_strategy}")
            logger.info(f"   - recommended_engine: {recommended_crawler}")
            logger.info(f"   - fallback_engines: {fallback_crawlers}")
            print(f"[DEBUG] 🔧 추출된 전략 정보:")
            print(f"[DEBUG]    - crawling_strategy: {crawling_strategy}")
            print(f"[DEBUG]    - recommended_engine: {recommended_crawler}")
            print(f"[DEBUG]    - fallback_engines: {fallback_crawlers}")
            
            # 항상 표시되는 MCP 분석 결과 (콘솔 직접 출력)
            print(f"[MCP] 🧠 분석 결과: 추천={recommended_crawler}, 폴백={fallback_crawlers}")
            print(f"[MCP] 📋 최종 엔진 우선순위: {[recommended_crawler] + [c for c in fallback_crawlers if c != recommended_crawler]}")
            
            logger.info(f"🧠 MCP 분석 결과:")
            logger.info(f"   - 추천 엔진: {recommended_crawler}")
            logger.info(f"   - 폴백 엔진: {fallback_crawlers}")
            
            # CrawlStrategy 객체 생성
            logger.debug(f"🔧 recommended_crawler: {recommended_crawler}")
            logger.debug(f"🔧 fallback_crawlers: {fallback_crawlers}")
            
            engine_priority = [recommended_crawler] + [c for c in fallback_crawlers if c != recommended_crawler]
            logger.info(f"📋 최종 엔진 우선순위: {engine_priority}")
            logger.debug(f"🔧 엔진 우선순위 상세:")
            logger.debug(f"   - recommended_crawler: {recommended_crawler}")
            logger.debug(f"   - fallback_crawlers: {fallback_crawlers}")  
            logger.debug(f"   - 중복 제거 후: {[c for c in fallback_crawlers if c != recommended_crawler]}")
            logger.debug(f"   - 최종 조합: {engine_priority}")
            
            # 사용 가능한 엔진만 필터링
            available_engines = [eng for eng in engine_priority if eng in self.engines]
            unavailable_engines = [eng for eng in engine_priority if eng not in self.engines]
            
            # 🔧 디버깅: 엔진 필터링 결과
            logger.info(f"🔧 DEBUG: 엔진 필터링 결과:")
            logger.info(f"   - 요청된 엔진들: {engine_priority}")
            logger.info(f"   - 사용 가능한 엔진들: {available_engines}")
            logger.info(f"   - 사용 불가능한 엔진들: {unavailable_engines}")
            logger.info(f"   - 현재 초기화된 엔진들: {list(self.engines.keys())}")
            
            if unavailable_engines:
                logger.warning(f"⚠️ 사용 불가 엔진들: {unavailable_engines}")
            
            # 🔧 사용 가능한 엔진이 없는 경우 모든 엔진 사용
            if not available_engines:
                logger.warning(f"⚠️ 요청된 엔진들이 모두 사용 불가! 사용 가능한 모든 엔진 사용")
                available_engines = list(self.engines.keys())
            
            print(f"[MCP] ✅ 사용 가능한 엔진들: {available_engines}")
            logger.info(f"✅ 사용 가능한 엔진들: {available_engines}")
            logger.debug(f"🔍 self.engines.keys(): {list(self.engines.keys())}")
            
            strategy = CrawlStrategy(
                engine_priority=available_engines,
                timeout=30,
                max_retries=3,
                wait_time=1.0
            )
            
            print(f"[MCP] 🎯 최종 전략: 우선순위={available_engines}")
            logger.info(f"🎯 MCP 추천 전략: {recommended_crawler} (폴백: {fallback_crawlers})")
            logger.info(f"🔧 실제 사용할 우선순위: {available_engines}")
        
        # 우선순위에 따라 엔진 시도
        last_error = None
        attempted_engines = []
        
        logger.info(f"🎯 엔진 우선순위: {strategy.engine_priority}")
        logger.info(f"🎬 크롤링 시작: 총 {len(strategy.engine_priority)}개 엔진 시도 예정")
        print(f"[DEBUG] 🎯 엔진 우선순위: {strategy.engine_priority}")
        print(f"[DEBUG] 🎬 크롤링 시작: 총 {len(strategy.engine_priority)}개 엔진 시도 예정")
        
        for i, engine_name in enumerate(strategy.engine_priority, 1):
            attempted_engines.append(engine_name)
            
            if engine_name not in self.engines:
                logger.warning(f"⚠️ [{i}/{len(strategy.engine_priority)}] 엔진 {engine_name} 사용 불가 (등록되지 않음)")
                logger.warning(f"🔧 DEBUG: 현재 등록된 엔진들: {list(self.engines.keys())}")
                continue
            
            engine = self.engines[engine_name]
            logger.info(f"🚀 [{i}/{len(strategy.engine_priority)}] {engine_name} 엔진으로 크롤링 시도 중...")
            print(f"[DEBUG] 🚀 [{i}/{len(strategy.engine_priority)}] {engine_name} 엔진으로 크롤링 시도 중...")
            
            try:
                start_time = asyncio.get_event_loop().time()
                result = await engine.crawl_with_retry(url, strategy)
                end_time = asyncio.get_event_loop().time()
                execution_time = end_time - start_time
                
                logger.info(f"⏱️ {engine_name} 엔진 실행 시간: {execution_time:.2f}초")
                logger.info(f"📊 {engine_name} 엔진 결과: status={result.status}, title='{result.title}', text_length={len(result.text)}")
                
                if result.status == "complete":
                    logger.info(f"✅ [{i}/{len(strategy.engine_priority)}] {engine_name} 엔진으로 성공!")
                    logger.info(f"🎉 최종 선택된 엔진: {engine_name}")
                    
                    # 성공한 엔진 정보를 메타데이터에 추가
                    result.metadata["attempted_engines"] = attempted_engines
                    result.metadata["successful_engine_index"] = i
                    result.metadata["total_available_engines"] = len(strategy.engine_priority)
                    
                    # 실제 처리시간 추가 (기존 하드코딩된 값 덮어쓰기)
                    result.metadata["processing_time"] = f"{execution_time:.2f}s"
                    result.metadata["execution_time"] = execution_time
                    result.metadata["engine_used"] = engine_name
                    
                    # MCP 품질 검증 실행 (오류 시 무시)
                    if analysis_result and self.mcp_tools_manager:
                        try:
                            async with self.mcp_client.connect():
                                quality_result = await self.mcp_tools_manager.validate_crawling_quality(
                                    result.to_dict(), url
                                )
                                
                                # 품질 정보를 결과에 추가
                                if quality_result and "error" not in quality_result:
                                    result.metadata["mcp_quality_score"] = quality_result.get("quality_score", "N/A")
                                    result.metadata["quality_assessment"] = quality_result.get("assessment", {})
                                    logger.info(f"📊 MCP 품질 점수: {quality_result.get('quality_score', 'N/A')}")
                                else:
                                    logger.debug("MCP 품질 검증 결과 없음 또는 오류")
                        except Exception as e:
                            logger.debug(f"MCP 품질 검증 스킵 (오류): {e}")
                            # 품질 검증 실패해도 크롤링 결과에는 영향 없음
                    
                    # MCP 분석 정보 추가
                    if analysis_result:
                        result.metadata["mcp_analysis"] = analysis_result
                        result.metadata["used_mcp_intelligence"] = True
                        
                        # 🎯 사용자 친화적인 엔진 선택 이유 생성
                        engine_selection_reason = self._generate_engine_selection_explanation(
                            analysis_result, engine_name, attempted_engines
                        )
                        result.metadata["engine_selection_reason"] = engine_selection_reason
                    
                    return result
                else:
                    logger.warning(f"⚠️ [{i}/{len(strategy.engine_priority)}] {engine_name} 엔진 부분 실패: {result.error}")
                    last_error = result.error
                    
            except Exception as e:
                logger.error(f"❌ [{i}/{len(strategy.engine_priority)}] {engine_name} 엔진 예외 발생: {type(e).__name__}: {e}")
                last_error = str(e)
                continue
        
        # 모든 엔진 실패
        logger.error(f"💥 모든 엔진 실패: {url}")
        logger.error(f"🔍 시도한 엔진들: {attempted_engines}")
        logger.error(f"📝 마지막 오류: {last_error}")
        
        return CrawlResult(
            url=url,
            title="",
            text="",
            hierarchy={},
            metadata={
                "attempted_engines": attempted_engines,
                "total_available_engines": len(strategy.engine_priority),
                "final_error": str(last_error),
                "all_engines_failed": True
            },
            status="failed",
            timestamp=datetime.now(),
            error=f"모든 엔진 실패: {last_error}"
        )
    
    async def bulk_crawl(self, urls: List[str], max_concurrent: int = 5) -> List[CrawlResult]:
        """대량 URL 병렬 크롤링"""
        logger.info(f"📦 대량 크롤링 시작: {len(urls)}개 URL")
        
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def crawl_single(url: str) -> CrawlResult:
            async with semaphore:
                return await self.crawl_with_strategy(url)
        
        tasks = [crawl_single(url) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 예외 처리
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append(CrawlResult(
                    url=urls[i],
                    title="",
                    text="",
                    hierarchy={},
                    metadata={"error": str(result)},
                    status="failed",
                    timestamp=datetime.now(),
                    error=str(result)
                ))
            else:
                processed_results.append(result)
        
        success_count = sum(1 for r in processed_results if r.status == "complete")
        logger.info(f"📊 대량 크롤링 완료: {success_count}/{len(urls)} 성공")
        
        return processed_results
    
    def _generate_engine_selection_explanation(self, analysis_result: Dict, selected_engine: str, attempted_engines: List[str]) -> Dict[str, Any]:
        """사용자 친화적인 엔진 선택 이유 생성"""
        try:
            site_analysis = analysis_result.get("site_analysis", {})
            crawling_strategy = analysis_result.get("crawling_strategy", {})
            
            # 사이트 특성 분석
            site_type = site_analysis.get("site_type", {}).get("type", "unknown")
            js_complexity = site_analysis.get("javascript_complexity", {})
            anti_bot = site_analysis.get("anti_bot_detection", {})
            
            # 기본 정보
            explanation = {
                "selected_engine": selected_engine,
                "confidence": crawling_strategy.get("confidence", 0),
                "analysis_method": "MCP AI 분석" if not analysis_result.get("is_fallback") else "폴백 전략",
                "site_characteristics": {},
                "selection_reasons": [],
                "technical_details": {},
                "fallback_engines": crawling_strategy.get("fallback_engines", [])
            }
            
            # 사이트 특성 요약
            explanation["site_characteristics"] = {
                "site_type": site_type,
                "javascript_level": js_complexity.get("level", "unknown"),
                "javascript_score": js_complexity.get("score", 0),
                "anti_bot_risk": anti_bot.get("risk_level", "unknown"),
                "requires_js": js_complexity.get("requires_js_execution", False)
            }
            
            # 선택 이유 생성
            reasons = []
            
            # 사이트 타입별 이유
            if site_type == "simple_static":
                reasons.append("정적 웹사이트로 분류되었습니다")
            elif site_type == "complex_spa":
                reasons.append("복잡한 SPA(Single Page Application)로 분석되었습니다")
            elif site_type == "dynamic_content":
                reasons.append("동적 콘텐츠가 포함된 사이트로 분석되었습니다")
            
            # JavaScript 복잡도 이유
            js_level = js_complexity.get("level", "unknown")
            js_score = js_complexity.get("score", 0)
            
            if js_level == "high" and js_score > 70:
                reasons.append(f"JavaScript 복잡도가 높음 (점수: {js_score}/100)")
                reasons.append("JavaScript 실행이 필요한 동적 콘텐츠가 포함되어 있습니다")
            elif js_level == "medium":
                reasons.append(f"JavaScript 복잡도가 보통 수준 (점수: {js_score}/100)")
            elif js_level == "low":
                reasons.append(f"JavaScript 사용량이 적음 (점수: {js_score}/100)")
            
            # 안티봇 위험도 이유
            anti_bot_risk = anti_bot.get("risk_level", "unknown")
            if anti_bot_risk == "high":
                reasons.append("강력한 봇 차단 시스템이 감지되었습니다")
            elif anti_bot_risk == "medium":
                reasons.append("중간 수준의 봇 차단 시스템이 있습니다")
            elif anti_bot_risk == "low":
                reasons.append("봇 차단 위험도가 낮습니다")
            
            # 엔진별 선택 이유
            if selected_engine == "crawl4ai":
                reasons.append("AI 기반 콘텐츠 추출에 최적화된 엔진입니다")
                if js_complexity.get("requires_js_execution"):
                    reasons.append("JavaScript 실행과 LLM 기반 추출이 필요합니다")
            elif selected_engine == "firecrawl":
                reasons.append("프리미엄 크롤링 서비스로 안티봇 우회에 강력합니다")
            elif selected_engine == "playwright":
                reasons.append("브라우저 자동화로 복잡한 사이트 처리에 적합합니다")
            elif selected_engine == "requests":
                reasons.append("단순한 HTTP 요청으로 빠른 처리가 가능합니다")
            
            explanation["selection_reasons"] = reasons
            
            # 기술적 세부사항
            explanation["technical_details"] = {
                "mcp_reasoning": crawling_strategy.get("reasoning", ""),
                "script_count": site_analysis.get("site_type", {}).get("script_count", 0),
                "content_ratio": site_analysis.get("site_type", {}).get("content_ratio", 0),
                "attempted_engines": attempted_engines,
                "success_on_attempt": len(attempted_engines)
            }
            
            return explanation
            
        except Exception as e:
            logger.error(f"엔진 선택 이유 생성 중 오류: {e}")
            return {
                "selected_engine": selected_engine,
                "confidence": 0,
                "analysis_method": "오류 발생",
                "selection_reasons": [f"{selected_engine} 엔진이 선택되었습니다"],
                "error": str(e)
            }

    async def get_engine_status(self) -> Dict[str, Any]:
        """모든 엔진 상태 반환"""
        status = {}
        
        for name, engine in self.engines.items():
            try:
                status[name] = await engine.health_check()
            except Exception as e:
                status[name] = {
                    "name": name,
                    "error": str(e),
                    "initialized": False
                }
        
        return {
            "total_engines": len(self.engines),
            "initialized": self.is_initialized,
            "engines": status
        } 