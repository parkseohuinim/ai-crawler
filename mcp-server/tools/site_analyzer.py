"""
사이트 분석 및 최적 크롤러 선택 도구
SPA/SSR/Static 판별, JavaScript 복잡도 분석, 안티봇 감지 등
"""

import re
import asyncio
import logging
from typing import Dict, Optional, List
import httpx
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

logger = logging.getLogger(__name__)

class SiteAnalyzer:
    """사이트 종합 분석 및 최적 크롤러 선택"""
    
    def __init__(self):
        self.session = httpx.AsyncClient(
            headers={
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            },
            timeout=30.0,
            follow_redirects=True,  # 리디렉션 자동 추적
            max_redirects=5  # 최대 5번까지 리디렉션 허용
        )
    
    async def analyze_and_select(
        self, 
        url: str, 
        sample_html: Optional[str] = None,
        headers: Optional[Dict] = None
    ) -> Dict:
        """
        사이트 종합 분석 및 최적 크롤러 선택
        
        Args:
            url: 분석할 웹사이트 URL
            sample_html: 사이트 샘플 HTML (선택사항)
            headers: HTTP 헤더 정보 (선택사항)
            
        Returns:
            분석 결과 및 추천 크롤러 정보
        """
        try:
            logger.info(f"사이트 분석 시작: {url}")
            
            # HTML 샘플 획득
            if not sample_html:
                sample_html = await self._fetch_sample_html(url)
            
            # 기본 분석 수행
            analysis_results = {
                "url": url,
                "site_type": await self._detect_site_type(sample_html, url),
                "javascript_complexity": await self._analyze_javascript_complexity(sample_html),
                "anti_bot_detection": await self._detect_anti_bot_systems(sample_html, headers or {}),
                "content_loading": await self._analyze_content_loading(sample_html),
                "performance_indicators": await self._get_performance_indicators(url, sample_html),
                "recommended_crawler": None,
                "fallback_crawlers": [],
                "extraction_hints": {}
            }
            
            # 최적 크롤러 선택
            crawler_recommendation = await self._select_optimal_crawler(analysis_results)
            analysis_results.update(crawler_recommendation)
            
            logger.info(f"사이트 분석 완료: {analysis_results['recommended_crawler']}")
            return analysis_results
            
        except Exception as e:
            logger.error(f"사이트 분석 오류: {e}")
            return {
                "url": url,
                "error": str(e),
                "recommended_crawler": "requests",  # 기본 폴백
                "fallback_crawlers": ["firecrawl"],
                "confidence": 0.1
            }
    
    async def _fetch_sample_html(self, url: str) -> str:
        """사이트에서 샘플 HTML 가져오기"""
        try:
            # 추가 헤더로 더 나은 호환성 확보
            extra_headers = {
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'ko-KR,ko;q=0.9,en;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1'
            }
            
            response = await self.session.get(url, headers=extra_headers)
            response.raise_for_status()
            
            logger.info(f"✅ HTML 샘플 획득 성공: {url} (상태: {response.status_code})")
            return response.text[:50000]  # 샘플링 제한
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 403:
                logger.warning(f"⚠️ 접근 금지 (403): {url} - 봇 차단 가능성")
            elif e.response.status_code == 404:
                logger.warning(f"⚠️ 페이지 없음 (404): {url}")
            else:
                logger.warning(f"⚠️ HTTP 오류 ({e.response.status_code}): {url}")
            return ""
        except httpx.RequestError as e:
            logger.warning(f"⚠️ 네트워크 오류: {url} - {e}")
            return ""
        except Exception as e:
            logger.warning(f"⚠️ HTML 샘플 획득 실패: {url} - {e}")
            return ""
    
    async def _detect_site_type(self, html: str, url: str) -> Dict:
        """사이트 타입 감지 (SPA/SSR/Static)"""
        soup = BeautifulSoup(html, 'html.parser')
        
        # JavaScript 프레임워크 감지
        frameworks = {
            'react': bool(re.search(r'react|ReactDOM', html, re.I)),
            'vue': bool(re.search(r'vue\.js|Vue\(', html, re.I)), 
            'angular': bool(re.search(r'angular|ng-app', html, re.I)),
            'svelte': bool(re.search(r'svelte', html, re.I)),
            'next': bool(re.search(r'__NEXT_DATA__|_next', html, re.I))
        }
        
        # 콘텐츠 분석
        script_tags = len(soup.find_all('script'))
        text_content = soup.get_text().strip()
        dom_nodes = len(soup.find_all())
        
        # SPA 특성 점수 계산
        spa_score = 0
        if script_tags > 10: spa_score += 30
        if any(frameworks.values()): spa_score += 40
        if 'data-reactroot' in html or '__NEXT_DATA__' in html: spa_score += 50
        if len(text_content) < 500 and dom_nodes > 50: spa_score += 30
        
        # 사이트 타입 결정
        if spa_score >= 70:
            site_type = "complex_spa"
        elif spa_score >= 40:
            site_type = "standard_dynamic"
        else:
            site_type = "simple_static"
            
        return {
            "type": site_type,
            "spa_score": spa_score,
            "frameworks": {k: v for k, v in frameworks.items() if v},
            "script_count": script_tags,
            "content_ratio": len(text_content) / max(len(html), 1)
        }
    
    async def _analyze_javascript_complexity(self, html: str) -> Dict:
        """JavaScript 복잡도 분석"""
        
        # JavaScript 패턴 분석
        js_patterns = {
            'ajax_calls': len(re.findall(r'\.ajax\(|fetch\(|axios\.|XMLHttpRequest', html, re.I)),
            'dynamic_imports': len(re.findall(r'import\(|require\(', html)),
            'event_listeners': len(re.findall(r'addEventListener|onClick|onLoad', html, re.I)),
            'dom_manipulation': len(re.findall(r'getElementById|querySelector|createElement', html, re.I)),
            'async_operations': len(re.findall(r'async|await|Promise|setTimeout', html, re.I))
        }
        
        # 복잡도 점수 계산
        complexity_score = sum(js_patterns.values()) * 2
        
        complexity_level = "low"
        if complexity_score > 100:
            complexity_level = "very_high"
        elif complexity_score > 50:
            complexity_level = "high" 
        elif complexity_score > 20:
            complexity_level = "medium"
            
        return {
            "level": complexity_level,
            "score": complexity_score,
            "patterns": js_patterns,
            "requires_js_execution": complexity_score > 30
        }
    
    async def _detect_anti_bot_systems(self, html: str, headers: Dict) -> Dict:
        """안티봇 시스템 감지"""
        
        anti_bot_indicators = {
            'cloudflare': 'cloudflare' in html.lower() or 'cf-ray' in str(headers).lower(),
            'recaptcha': 'recaptcha' in html.lower() or 'grecaptcha' in html.lower(),
            'captcha': 'captcha' in html.lower(),
            'bot_detection': any(pattern in html.lower() for pattern in [
                'distil_r_captcha', 'perimeterx', 'imperva', 'akamai', 'datadome'
            ]),
            'rate_limiting': any(header in str(headers).lower() for header in [
                'x-ratelimit', 'retry-after', 'x-rate-limit'
            ]),
            'js_challenge': 'challenge' in html.lower() and 'javascript' in html.lower()
        }
        
        # 위험도 평가
        risk_score = sum(anti_bot_indicators.values()) * 25
        
        risk_level = "low"
        if risk_score >= 75:
            risk_level = "very_high"
        elif risk_score >= 50:
            risk_level = "high"
        elif risk_score >= 25:
            risk_level = "medium"
            
        return {
            "risk_level": risk_level,
            "risk_score": risk_score,
            "detected_systems": {k: v for k, v in anti_bot_indicators.items() if v},
            "bypass_strategy": self._get_bypass_strategy(risk_level)
        }
    
    async def _analyze_content_loading(self, html: str) -> Dict:
        """콘텐츠 로딩 방식 분석"""
        
        loading_patterns = {
            'infinite_scroll': bool(re.search(r'infinite.?scroll|lazy.?load', html, re.I)),
            'pagination': bool(re.search(r'pagination|page-\d+|next-page', html, re.I)),
            'ajax_content': bool(re.search(r'load-more|ajax-load|dynamic-content', html, re.I)),
            'single_page': 'data-page' in html or 'single-page' in html,
            'requires_interaction': bool(re.search(r'click-to-load|show-more|expand', html, re.I))
        }
        
        return {
            "patterns": loading_patterns,
            "requires_scrolling": loading_patterns['infinite_scroll'],
            "requires_interaction": loading_patterns['requires_interaction'],
            "loading_strategy": "static" if not any(loading_patterns.values()) else "dynamic"
        }
    
    async def _get_performance_indicators(self, url: str, html: str) -> Dict:
        """성능 지표 분석"""
        
        domain = urlparse(url).netloc
        
        return {
            "estimated_size": len(html),
            "script_heavy": html.count('<script') > 20,
            "image_heavy": html.count('<img') > 50,
            "external_resources": len(re.findall(r'src=["\'](https?://[^"\']+)', html)),
            "domain": domain,
            "likely_cdn": any(cdn in domain.lower() for cdn in ['cdn', 'static', 'assets'])
        }
    
    async def _select_optimal_crawler(self, analysis: Dict) -> Dict:
        """분석 결과를 바탕으로 최적 크롤러 선택"""
        
        site_type = analysis["site_type"]["type"]
        js_complexity = analysis["javascript_complexity"]["level"]
        anti_bot_risk = analysis["anti_bot_detection"]["risk_level"]
        
        # 크롤러 선택 로직 (PROJECT_SPECIFICATION.md 기반)
        if anti_bot_risk in ["high", "very_high"]:
            # 강한 안티봇이 있는 경우 Firecrawl 우선
            recommended = "firecrawl"
            fallbacks = ["playwright", "crawl4ai", "requests"]
            confidence = 0.8
            
        elif site_type == "complex_spa" or js_complexity in ["high", "very_high"]:
            # 복잡한 SPA인 경우
            if analysis["anti_bot_detection"]["risk_score"] > 25:
                recommended = "firecrawl"  # 안티봇이 있으면 Firecrawl
                fallbacks = ["crawl4ai", "playwright", "requests"]
            else:
                recommended = "crawl4ai"   # AI 분석이 필요한 경우
                fallbacks = ["firecrawl", "playwright", "requests"]
            confidence = 0.9
            
        elif site_type == "standard_dynamic":
            # 표준 동적 사이트
            recommended = "playwright"
            fallbacks = ["crawl4ai", "firecrawl", "requests"]
            confidence = 0.85
            
        else:
            # 단순 정적 사이트
            recommended = "requests"
            fallbacks = ["playwright", "firecrawl"]
            confidence = 0.75
        
        # 추출 힌트 생성
        extraction_hints = {
            "wait_for_js": js_complexity in ["high", "very_high"],
            "scroll_needed": analysis["content_loading"]["requires_scrolling"],
            "interaction_needed": analysis["content_loading"]["requires_interaction"],
            "bypass_strategy": analysis["anti_bot_detection"]["bypass_strategy"]
        }
        
        return {
            "recommended_crawler": recommended,
            "fallback_crawlers": fallbacks,
            "confidence": confidence,
            "extraction_hints": extraction_hints,
            "reasoning": f"{site_type} 사이트, {js_complexity} JS 복잡도, {anti_bot_risk} 안티봇 위험도"
        }
    
    def _get_bypass_strategy(self, risk_level: str) -> str:
        """안티봇 우회 전략 제안"""
        strategies = {
            "low": "standard_headers",
            "medium": "rotating_user_agents", 
            "high": "premium_proxy_rotation",
            "very_high": "professional_service_required"
        }
        return strategies.get(risk_level, "standard_headers") 