"""
크롤링 전략 관리자
MCP 분석 결과를 바탕으로 크롤링 전략을 수립하고 관리
"""

import logging
from typing import Dict, Any, List, Optional
from .client import MCPClient

logger = logging.getLogger(__name__)

class CrawlingStrategyManager:
    """크롤링 전략을 관리하는 매니저 클래스"""
    
    # 크롤러별 특성 정의 (PROJECT_SPECIFICATION.md 기반)
    CRAWLER_CHARACTERISTICS = {
        "firecrawl": {
            "strengths": ["SPA", "안티봇 우회", "복잡한 JS", "React/Vue"],
            "weaknesses": ["비용", "API 제한"],
            "use_cases": ["complex_spa", "anti_bot_heavy"]
        },
        "crawl4ai": {
            "strengths": ["AI 분석", "의미적 추출", "구조화"],
            "weaknesses": ["속도", "리소스 사용량"],
            "use_cases": ["ai_analysis_needed", "complex_structure"]
        },
        "playwright": {
            "strengths": ["정밀 제어", "로그인", "인터랙션"],
            "weaknesses": ["리소스 사용량", "복잡성"],
            "use_cases": ["standard_dynamic", "login_required"]
        },
        "requests": {
            "strengths": ["속도", "단순함", "안정성"],
            "weaknesses": ["JS 처리 불가", "동적 콘텐츠"],
            "use_cases": ["simple_static", "api_endpoints"]
        }
    }
    
    def __init__(self, mcp_client: MCPClient):
        """
        크롤링 전략 매니저 초기화
        
        Args:
            mcp_client: MCP 클라이언트 인스턴스
        """
        self.mcp_client = mcp_client
        self._strategy_cache = {}
    
    async def create_crawling_strategy(self, url: str, site_analysis: Dict[str, Any] = None,
                                     structure_analysis: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        URL에 대한 종합적인 크롤링 전략 생성
        
        Args:
            url: 대상 URL
            site_analysis: 사이트 분석 결과 (없으면 자동 분석)
            structure_analysis: 구조 분석 결과 (없으면 자동 분석)
            
        Returns:
            완전한 크롤링 전략
        """
        logger.info(f"크롤링 전략 생성 시작: {url}")
        
        try:
            # 🚨 캐시 비활성화 (디버깅용) - 각 URL마다 새로운 전략 생성
            # if url in self._strategy_cache:
            #     logger.info(f"캐시된 전략 사용: {url}")
            #     return self._strategy_cache[url]
            
            logger.info(f"🔄 새로운 전략 생성 (캐시 비활성화): {url}")
            
            # 사이트 분석이 없으면 실행
            if not site_analysis:
                logger.info("사이트 분석 실행 중...")
                site_analysis = await self.mcp_client.analyze_site(url)
                
                if "error" in site_analysis:
                    logger.error(f"사이트 분석 실패: {site_analysis['error']}")
                    return self._create_fallback_strategy(url)
            
            # 구조 분석이 없으면 실행
            if not structure_analysis:
                logger.info("구조 분석 실행 중...")
                structure_analysis = await self.mcp_client.detect_structure("", url)
                
                if "error" in structure_analysis:
                    logger.warning(f"구조 분석 실패, 기본 구조 사용: {structure_analysis['error']}")
                    structure_analysis = {"basic_structure": True}
            
            # MCP를 통한 전략 생성
            logger.info("MCP 전략 생성 실행 중...")
            mcp_strategy = await self.mcp_client.generate_strategy(site_analysis, structure_analysis)
            
            if "error" in mcp_strategy:
                logger.error(f"MCP 전략 생성 실패: {mcp_strategy['error']}")
                return self._create_fallback_strategy(url)
            
            # 전략 보강 및 최적화
            enhanced_strategy = self._enhance_strategy(url, site_analysis, structure_analysis, mcp_strategy)
            
            # 캐시에 저장
            # self._strategy_cache[url] = enhanced_strategy
            
            logger.info(f"크롤링 전략 생성 완료: {url}")
            return enhanced_strategy
            
        except Exception as e:
            logger.error(f"크롤링 전략 생성 오류: {e}")
            return self._create_fallback_strategy(url)
    
    def _enhance_strategy(self, url: str, site_analysis: Dict[str, Any], 
                         structure_analysis: Dict[str, Any], mcp_strategy: Dict[str, Any]) -> Dict[str, Any]:
        """MCP 전략을 백엔드 요구사항에 맞게 보강"""
        
        # 기본 전략 구조
        enhanced_strategy = {
            "url": url,
            "primary_crawler": mcp_strategy.get("recommended_crawler", "requests"),
            "fallback_crawlers": [],
            "crawler_settings": {},
            "extraction_rules": {},
            "quality_thresholds": {
                "minimum_score": 70.0,
                "retry_threshold": 50.0
            },
            "timeout_settings": {
                "page_load": 30,
                "element_wait": 10,
                "total_timeout": 120
            },
            "site_characteristics": site_analysis.get("site_type", {}),
            "content_structure": structure_analysis.get("hierarchy", {}),
            "mcp_analysis": mcp_strategy
        }
        
        # 크롤러별 폴백 순서 설정
        primary_crawler = enhanced_strategy["primary_crawler"]
        enhanced_strategy["fallback_crawlers"] = self._get_fallback_order(primary_crawler, site_analysis)
        
        # 크롤러별 세부 설정
        enhanced_strategy["crawler_settings"] = self._get_crawler_settings(primary_crawler, site_analysis)
        
        # 추출 규칙 설정
        enhanced_strategy["extraction_rules"] = self._get_extraction_rules(structure_analysis)
        
        return enhanced_strategy
    
    def _get_fallback_order(self, primary_crawler: str, site_analysis: Dict[str, Any]) -> List[str]:
        """주 크롤러에 따른 폴백 순서 결정"""
        all_crawlers = ["firecrawl", "crawl4ai", "playwright", "requests"]
        fallback_order = [c for c in all_crawlers if c != primary_crawler]
        
        # 사이트 특성에 따른 폴백 순서 최적화
        site_type = site_analysis.get("site_type", {}).get("type", "simple_static")
        
        if site_type == "complex_spa":
            # SPA의 경우 JS 처리 가능한 순서
            fallback_order = ["firecrawl", "playwright", "crawl4ai", "requests"]
        elif site_type == "anti_bot_heavy":
            # 안티봇이 강한 경우
            fallback_order = ["firecrawl", "playwright", "crawl4ai", "requests"]
        elif site_type == "simple_static":
            # 단순 정적 사이트
            fallback_order = ["requests", "playwright", "crawl4ai", "firecrawl"]
        
        # 주 크롤러 제거
        return [c for c in fallback_order if c != primary_crawler]
    
    def _get_crawler_settings(self, crawler: str, site_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """크롤러별 세부 설정"""
        base_settings = {
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "headers": {
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "ko-KR,ko;q=0.8,en-US;q=0.5,en;q=0.3",
                "Accept-Encoding": "gzip, deflate",
                "DNT": "1",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
            }
        }
        
        if crawler == "firecrawl":
            base_settings.update({
                "formats": ["markdown", "html"],
                "includeTags": ["article", "main", "content"],
                "excludeTags": ["nav", "footer", "aside", "script"],
                "onlyMainContent": True
            })
        elif crawler == "playwright":
            base_settings.update({
                "wait_for_selector": "body",
                "wait_for_load_state": "networkidle",
                "screenshot": False,
                "full_page": True
            })
        elif crawler == "crawl4ai":
            base_settings.update({
                "word_count_threshold": 50,
                "extraction_strategy": "LLMExtractionStrategy",
                "chunking_strategy": "RegexChunking"
            })
        
        return base_settings
    
    def _get_extraction_rules(self, structure_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """콘텐츠 추출 규칙 생성"""
        rules = {
            "title_selectors": ["h1", "title", ".title", "#title"],
            "content_selectors": ["article", "main", ".content", "#content", ".post", ".article"],
            "exclude_selectors": ["nav", "footer", "aside", ".sidebar", ".ads", ".advertisement"],
            "text_filters": {
                "min_length": 10,
                "max_length": 100000,
                "remove_extra_whitespace": True,
                "normalize_unicode": True
            }
        }
        
        # 구조 분석 결과 반영
        if "hierarchy" in structure_analysis:
            hierarchy = structure_analysis["hierarchy"]
            if "headings" in hierarchy:
                # 발견된 헤딩 태그 우선 사용
                heading_tags = list(hierarchy["headings"].keys())
                if heading_tags:
                    rules["title_selectors"] = heading_tags + rules["title_selectors"]
        
        return rules
    
    def _create_fallback_strategy(self, url: str) -> Dict[str, Any]:
        """오류 시 사용할 기본 폴백 전략"""
        logger.warning(f"폴백 전략 사용: {url}")
        
        return {
            "url": url,
            "primary_crawler": "requests",
            "fallback_crawlers": ["playwright", "crawl4ai", "firecrawl"],
            "crawler_settings": self._get_crawler_settings("requests", {}),
            "extraction_rules": self._get_extraction_rules({}),
            "quality_thresholds": {
                "minimum_score": 50.0,  # 낮은 임계값
                "retry_threshold": 30.0
            },
            "timeout_settings": {
                "page_load": 30,
                "element_wait": 10,
                "total_timeout": 120
            },
            "is_fallback": True,
            "error": "MCP 전략 생성 실패로 인한 폴백 전략 사용"
        }
    
    def get_strategy_summary(self, strategy: Dict[str, Any]) -> str:
        """전략 요약 문자열 생성"""
        primary = strategy.get("primary_crawler", "unknown")
        fallbacks = strategy.get("fallback_crawlers", [])
        site_type = strategy.get("site_characteristics", {}).get("type", "unknown")
        
        return f"주 크롤러: {primary}, 폴백: {' → '.join(fallbacks)}, 사이트 유형: {site_type}" 