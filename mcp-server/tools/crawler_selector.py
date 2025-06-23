"""
추출 전략 수립 도구
엔진별 최적 설정, CSS 셀렉터 규칙, 제외 영역 정의, 후처리 방법
"""

import logging
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)

class CrawlerSelector:
    """추출 전략 수립 및 크롤러 설정 생성"""
    
    def __init__(self):
        # 엔진별 기본 설정 템플릿
        self.engine_configs = {
            "firecrawl": {
                "formats": ["markdown", "html"],
                "timeout": 30000,
                "wait_for": "networkidle",
                "screenshot": False,
                "extract": {
                    "schema": {}
                }
            },
            "crawl4ai": {
                "word_count_threshold": 10,
                "extraction_strategy": "LLMExtractionStrategy",
                "chunking_strategy": "RegexChunking",
                "css_selector": "",
                "wait_for": "domcontentloaded"
            },
            "playwright": {
                "wait_until": "networkidle",
                "timeout": 30000,
                "viewport": {"width": 1920, "height": 1080},
                "user_agent": "Mozilla/5.0 (compatible; AIBot/1.0)",
                "extra_headers": {}
            },
            "requests": {
                "timeout": 45,  # 30초 → 45초로 증가
                "headers": {
                    "User-Agent": "Mozilla/5.0 (compatible; AIBot/1.0)"
                },
                "verify_ssl": True,
                "allow_redirects": True,
                "max_retries": 3,
                "backoff_factor": 1.0
            }
        }
    
    async def generate_strategy(
        self, 
        site_analysis: Dict, 
        content_structure: Dict
    ) -> Dict:
        """
        추출 전략 수립
        
        Args:
            site_analysis: 사이트 분석 결과
            content_structure: 콘텐츠 구조 분석 결과
            
        Returns:
            추출 전략 및 엔진별 설정
        """
        try:
            logger.info(f"추출 전략 수립 시작: {site_analysis.get('url', 'Unknown')}")
            
            # 기본 전략 정보
            strategy = {
                "url": site_analysis.get("url"),
                "recommended_engine": site_analysis.get("recommended_crawler"),
                "fallback_engines": site_analysis.get("fallback_crawlers", []),
                "confidence": site_analysis.get("confidence", 0.7),
                "engine_configs": {},
                "extraction_rules": {},
                "post_processing": {},
                "quality_thresholds": {}
            }
            
            # 각 엔진별 최적화된 설정 생성
            all_engines = [strategy["recommended_engine"]] + strategy["fallback_engines"]
            
            for engine in all_engines:
                if engine:
                    strategy["engine_configs"][engine] = await self._create_engine_config(
                        engine, site_analysis, content_structure
                    )
            
            # 추출 규칙 생성
            strategy["extraction_rules"] = await self._generate_extraction_rules(
                site_analysis, content_structure
            )
            
            # 후처리 전략 생성
            strategy["post_processing"] = await self._create_post_processing_strategy(
                site_analysis, content_structure
            )
            
            # 품질 임계값 설정
            strategy["quality_thresholds"] = await self._set_quality_thresholds(
                site_analysis, content_structure
            )
            
            logger.info("추출 전략 수립 완료")
            return strategy
            
        except Exception as e:
            logger.error(f"전략 수립 오류: {e}")
            return {
                "url": site_analysis.get("url"),
                "error": str(e),
                "recommended_engine": "requests",
                "engine_configs": {"requests": self.engine_configs["requests"]},
                "confidence": 0.1
            }
    
    async def _create_engine_config(
        self, 
        engine: str, 
        site_analysis: Dict, 
        content_structure: Dict
    ) -> Dict:
        """엔진별 최적화된 설정 생성"""
        
        base_config = self.engine_configs.get(engine, {}).copy()
        
        if engine == "firecrawl":
            return await self._optimize_firecrawl_config(
                base_config, site_analysis, content_structure
            )
        elif engine == "crawl4ai":
            return await self._optimize_crawl4ai_config(
                base_config, site_analysis, content_structure
            )
        elif engine == "playwright":
            return await self._optimize_playwright_config(
                base_config, site_analysis, content_structure
            )
        elif engine == "requests":
            return await self._optimize_requests_config(
                base_config, site_analysis, content_structure
            )
        
        return base_config
    
    async def _optimize_firecrawl_config(
        self, config: Dict, site_analysis: Dict, content_structure: Dict
    ) -> Dict:
        """Firecrawl 엔진 최적화"""
        
        # 안티봇 대응
        anti_bot_risk = site_analysis.get("anti_bot_detection", {}).get("risk_level", "low")
        if anti_bot_risk in ["high", "very_high"]:
            config["timeout"] = 60000  # 긴 타임아웃
            config["wait_for"] = "networkidle"
            
        # JavaScript 복잡도에 따른 대기 시간
        js_complexity = site_analysis.get("javascript_complexity", {}).get("level", "low")
        if js_complexity in ["high", "very_high"]:
            config["wait_for"] = "networkidle"
            config["timeout"] = max(config.get("timeout", 30000), 45000)
        
        # 콘텐츠 구조에 따른 추출 스키마
        extraction_hints = content_structure.get("data_extraction_hints", {})
        if extraction_hints.get("content_selectors"):
            config["extract"]["schema"] = {
                "title": extraction_hints["title_selectors"][0] if extraction_hints.get("title_selectors") else "h1",
                "content": extraction_hints["content_selectors"][0] if extraction_hints["content_selectors"] else "main",
                "metadata": {
                    "author": ".author, .byline, [rel='author']",
                    "date": "time, .date, .published",
                    "tags": ".tags, .categories, .tag"
                }
            }
        
        # 스크롤 필요시 설정
        if site_analysis.get("content_loading", {}).get("requires_scrolling"):
            config["actions"] = [
                {"type": "scroll", "direction": "down", "amount": 3}
            ]
        
        return config
    
    async def _optimize_crawl4ai_config(
        self, config: Dict, site_analysis: Dict, content_structure: Dict
    ) -> Dict:
        """Crawl4AI 엔진 최적화"""
        
        # 콘텐츠 품질에 따른 임계값 조정
        content_quality = content_structure.get("content_density", {}).get("content_quality", "medium")
        if content_quality == "high":
            config["word_count_threshold"] = 5
        elif content_quality == "low":
            config["word_count_threshold"] = 20
        
        # 주요 콘텐츠 선택자 설정
        extraction_hints = content_structure.get("data_extraction_hints", {})
        if extraction_hints.get("content_selectors"):
            config["css_selector"] = ", ".join(extraction_hints["content_selectors"][:3])
        
        # 복잡한 사이트의 경우 LLM 전략 사용
        site_type = site_analysis.get("site_type", {}).get("type", "simple_static")
        if site_type in ["complex_spa", "ai_analysis_needed"]:
            config["extraction_strategy"] = "LLMExtractionStrategy"
            config["instruction"] = """
            주요 콘텐츠를 마크다운 형식으로 추출하세요. 
            네비게이션, 광고, 푸터는 제외하고 본문 내용만 포함하세요.
            제목, 단락, 리스트 구조를 유지하세요.
            """
        
        # JavaScript 복잡도에 따른 대기 설정
        js_complexity = site_analysis.get("javascript_complexity", {}).get("level", "low")
        if js_complexity in ["high", "very_high"]:
            config["wait_for"] = "networkidle"
            config["delay_before_return_html"] = 3.0
        
        return config
    
    async def _optimize_playwright_config(
        self, config: Dict, site_analysis: Dict, content_structure: Dict
    ) -> Dict:
        """Playwright 엔진 최적화"""
        
        # 안티봇 대응 헤더 설정
        anti_bot_risk = site_analysis.get("anti_bot_detection", {}).get("risk_level", "low")
        if anti_bot_risk in ["medium", "high", "very_high"]:
            config["extra_headers"] = {
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "ko-KR,ko;q=0.8,en-US;q=0.5,en;q=0.3",
                "Accept-Encoding": "gzip, deflate",
                "DNT": "1",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1"
            }
        
        # JavaScript 복잡도에 따른 대기 전략
        js_complexity = site_analysis.get("javascript_complexity", {}).get("level", "low")
        if js_complexity in ["high", "very_high"]:
            config["wait_until"] = "networkidle"
            config["timeout"] = 60000
        
        # 콘텐츠 로딩 패턴에 따른 스크롤 설정
        content_loading = site_analysis.get("content_loading", {})
        if content_loading.get("requires_scrolling"):
            config["scroll_strategy"] = "infinite_scroll"
            config["scroll_pause"] = 2
        elif content_loading.get("requires_interaction"):
            config["interaction_strategy"] = "click_to_expand"
        
        # 반응형 사이트 대응
        layout = content_structure.get("layout_type", {})
        if layout.get("responsive"):
            config["viewport"] = {"width": 1920, "height": 1080}  # 데스크톱 우선
        
        return config
    
    async def _optimize_requests_config(
        self, config: Dict, site_analysis: Dict, content_structure: Dict
    ) -> Dict:
        """Requests 엔진 최적화"""
        
        # 기본 헤더 강화
        config["headers"].update({
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "ko-KR,ko;q=0.8,en-US;q=0.5,en;q=0.3",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive"
        })
        
        # 세션 사용 설정
        config["use_session"] = True
        config["max_retries"] = 3
        config["backoff_factor"] = 1.0
        
        # SSL 검증 관련
        performance = site_analysis.get("performance_indicators", {})
        if performance.get("likely_cdn"):
            config["verify_ssl"] = True
        
        return config
    
    async def _generate_extraction_rules(
        self, site_analysis: Dict, content_structure: Dict
    ) -> Dict:
        """콘텐츠 추출 규칙 생성"""
        
        extraction_hints = content_structure.get("data_extraction_hints", {})
        
        rules = {
            "include_selectors": extraction_hints.get("content_selectors", ["main", "article"]),
            "exclude_selectors": extraction_hints.get("exclude_selectors", [".ads", "nav", "footer"]),
            "title_selectors": extraction_hints.get("title_selectors", ["h1"]),
            "metadata_selectors": {
                "author": ".author, .byline, [rel='author']",
                "date": "time, .date, .published-date, .publish-date",
                "tags": ".tags a, .categories a, .tag, [rel='tag']",
                "description": "meta[name='description'], .description, .summary"
            },
            "text_processing": {
                "min_text_length": 50,
                "remove_extra_whitespace": True,
                "preserve_paragraphs": True,
                "extract_links": True
            }
        }
        
        # 계층구조 기반 우선순위
        hierarchy = content_structure.get("hierarchy", {})
        if hierarchy.get("quality") == "excellent":
            rules["extract_hierarchy"] = True
            rules["max_heading_levels"] = min(hierarchy.get("levels", 3), 6)
        
        # 네비게이션 정보 포함 여부
        navigation = content_structure.get("navigation", {})
        if navigation.get("has_breadcrumbs"):
            rules["extract_breadcrumbs"] = True
            rules["breadcrumb_selectors"] = [".breadcrumb", ".breadcrumbs", "[aria-label*='breadcrumb']"]
        
        return rules
    
    async def _create_post_processing_strategy(
        self, site_analysis: Dict, content_structure: Dict
    ) -> Dict:
        """후처리 전략 생성"""
        
        strategy = {
            "text_cleaning": {
                "remove_empty_lines": True,
                "normalize_whitespace": True,
                "remove_special_chars": False,
                "fix_encoding": True
            },
            "content_filtering": {
                "min_content_length": 100,
                "remove_navigation": True,
                "remove_advertisements": True,
                "remove_social_widgets": True
            },
            "structure_enhancement": {
                "preserve_headings": True,
                "preserve_lists": True,
                "preserve_tables": True,
                "generate_toc": False
            },
            "metadata_extraction": {
                "extract_images": True,
                "extract_links": True,
                "extract_dates": True,
                "extract_authors": True
            }
        }
        
        # 콘텐츠 품질에 따른 조정
        content_quality = content_structure.get("content_density", {}).get("content_quality", "medium")
        if content_quality == "low":
            strategy["content_filtering"]["min_content_length"] = 200
            strategy["text_cleaning"]["remove_special_chars"] = True
        
        # 사이트 타입에 따른 조정
        site_type = site_analysis.get("site_type", {}).get("type", "simple_static")
        if site_type == "complex_spa":
            strategy["structure_enhancement"]["generate_toc"] = True
            strategy["metadata_extraction"]["extract_dynamic_content"] = True
        
        return strategy
    
    async def _set_quality_thresholds(
        self, site_analysis: Dict, content_structure: Dict
    ) -> Dict:
        """품질 임계값 설정"""
        
        # 기본 임계값
        thresholds = {
            "min_text_length": 500,
            "min_quality_score": 60,
            "max_retry_attempts": 3,
            "success_indicators": {
                "has_main_content": True,
                "has_title": True,
                "text_to_html_ratio": 0.1
            }
        }
        
        # 사이트 복잡도에 따른 조정
        js_complexity = site_analysis.get("javascript_complexity", {}).get("level", "low")
        if js_complexity in ["high", "very_high"]:
            thresholds["min_quality_score"] = 50  # 복잡한 사이트는 낮은 기준
            thresholds["max_retry_attempts"] = 5
        
        # 콘텐츠 밀도에 따른 조정
        content_density = content_structure.get("content_density", {})
        if content_density.get("content_quality") == "high":
            thresholds["min_text_length"] = 300
            thresholds["success_indicators"]["text_to_html_ratio"] = 0.15
        elif content_density.get("content_quality") == "low":
            thresholds["min_text_length"] = 1000
            thresholds["success_indicators"]["text_to_html_ratio"] = 0.05
        
        # 안티봇 위험도에 따른 조정
        anti_bot_risk = site_analysis.get("anti_bot_detection", {}).get("risk_level", "low")
        if anti_bot_risk in ["high", "very_high"]:
            thresholds["max_retry_attempts"] = 2  # 제한적 재시도
            thresholds["min_quality_score"] = 40  # 낮은 기준 적용
        
        return thresholds 