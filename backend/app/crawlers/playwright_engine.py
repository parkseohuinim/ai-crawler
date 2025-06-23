import os
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import asyncio
import json
from urllib.parse import urljoin, urlparse

from .base import BaseCrawler, CrawlResult, CrawlStrategy, EngineCapabilities

logger = logging.getLogger(__name__)

try:
    from playwright.async_api import async_playwright, Browser, BrowserContext, Page
    from playwright._impl._errors import Error as PlaywrightError, TimeoutError as PlaywrightTimeoutError
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    logger.warning("Playwright 라이브러리가 설치되지 않았습니다")

class PlaywrightEngine(BaseCrawler):
    """Playwright 기반 크롤링 엔진 - 브라우저 자동화 기반 고급 크롤링"""
    
    def __init__(self):
        super().__init__("playwright")
        self.playwright = None
        self.browser = None
        self.context = None
    
    async def initialize(self) -> None:
        """Playwright 브라우저 초기화"""
        if not PLAYWRIGHT_AVAILABLE:
            raise RuntimeError("Playwright 라이브러리가 설치되지 않았습니다")
        
        try:
            # Playwright 시작
            self.playwright = await async_playwright().start()
            
            # 브라우저 시작 (Chromium 사용)
            self.browser = await self.playwright.chromium.launch(
                headless=True,
                args=[
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-accelerated-2d-canvas',
                    '--disable-gpu',
                    '--window-size=1920,1080'
                ]
            )
            
            # 브라우저 컨텍스트 생성
            self.context = await self.browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                # 안티봇 설정
                java_script_enabled=True,
                bypass_csp=True,
                # 추가 헤더
                extra_http_headers={
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
                    'Accept-Language': 'ko-KR,ko;q=0.8,en-US;q=0.5,en;q=0.3',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'DNT': '1',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1',
                }
            )
            
            self.is_initialized = True
            logger.info("🎭 Playwright 엔진 초기화 완료")
            
        except Exception as e:
            logger.error(f"Playwright 초기화 실패: {e}")
            await self.cleanup()
            raise
    
    async def cleanup(self) -> None:
        """리소스 정리"""
        try:
            if self.context:
                await self.context.close()
                logger.info("🎭 Playwright 컨텍스트 종료 완료")
                
            if self.browser:
                await self.browser.close()
                logger.info("🎭 Playwright 브라우저 종료 완료")
                
            if self.playwright:
                await self.playwright.stop()
                logger.info("🎭 Playwright 종료 완료")
                
        except Exception as e:
            logger.error(f"Playwright 정리 중 오류: {e}")
        finally:
            self.context = None
            self.browser = None
            self.playwright = None
            self.is_initialized = False
            
        logger.info("🎭 Playwright 엔진 정리 완료")
    
    def get_capabilities(self) -> Dict[str, Any]:
        """Playwright 엔진의 능력"""
        return {
            EngineCapabilities.JAVASCRIPT_RENDERING: True,
            EngineCapabilities.ANTI_BOT_BYPASS: True,
            EngineCapabilities.PREMIUM_SERVICE: False,  # 오픈소스
            EngineCapabilities.INFINITE_SCROLL: True,
            EngineCapabilities.BULK_PROCESSING: True,
            "supported_formats": ["markdown", "html", "screenshot", "pdf"],
            "interaction_features": ["click", "scroll", "form_fill", "wait_for_elements"],
            "browser_features": ["full_js_execution", "network_interception", "cookie_management"],
            "rate_limits": "브라우저 기반 (무제한)",
            "best_for": ["복잡한 SPA", "인터랙션 필요 사이트", "안티봇 우회", "스크린샷 필요"]
        }
    
    async def _wait_for_content_load(self, page: Page, strategy: CrawlStrategy) -> None:
        """활동 기반 콘텐츠 로딩 대기"""
        import time
        
        start_time = time.time()
        logger.info(f"🎭 활동 기반 페이지 로딩 시작 (최대: {strategy.max_total_time}s)")
        
        try:
            # 1단계: 기본 DOM 로딩 대기 (빠른 타임아웃)
            await page.wait_for_load_state('domcontentloaded', timeout=strategy.timeout * 1000)
            
            # 2단계: 활동 기반 완료 대기
            await self._wait_for_loading_activity(page, strategy, start_time)
                
        except PlaywrightTimeoutError:
            elapsed = time.time() - start_time
            logger.warning(f"⚠️ 기본 로딩 타임아웃 ({elapsed:.1f}s) - 현재 상태로 진행")
    
    async def _wait_for_loading_activity(self, page: Page, strategy: CrawlStrategy, start_time: float) -> None:
        """로딩 활동이 완료될 때까지 대기"""
        import time
        
        last_activity_time = time.time()
        content_size_history = []
        network_idle_count = 0
        
        logger.info(f"📊 로딩 활동 모니터링 시작...")
        
        while True:
            current_time = time.time()
            
            # 최대 시간 초과 체크
            if current_time - start_time > strategy.max_total_time:
                logger.warning(f"⏰ 최대 시간 초과 ({strategy.max_total_time}s) - 강제 완료")
                break
            
            try:
                # 현재 콘텐츠 크기 측정
                content_size = await page.evaluate("""
                    () => {
                        const html = document.documentElement.outerHTML;
                        const scripts = document.querySelectorAll('script').length;
                        const images = document.querySelectorAll('img').length;
                        return {
                            htmlSize: html.length,
                            scriptCount: scripts,
                            imageCount: images,
                            readyState: document.readyState
                        };
                    }
                """)
                
                content_size_history.append(content_size)
                
                # 최근 활동 확인 (지난 3초간 변화 확인)
                if len(content_size_history) > 3:
                    recent_sizes = content_size_history[-3:]
                    size_changes = [
                        abs(recent_sizes[i]['htmlSize'] - recent_sizes[i-1]['htmlSize']) 
                        for i in range(1, len(recent_sizes))
                    ]
                    
                    # 변화가 있으면 활동으로 간주
                    if any(change > 1000 for change in size_changes):  # 1KB 이상 변화
                        last_activity_time = current_time
                        network_idle_count = 0
                        logger.debug(f"📈 콘텐츠 변화 감지: {max(size_changes)/1024:.1f}KB")
                    else:
                        network_idle_count += 1
                
                # 네트워크 상태 확인
                try:
                    await page.wait_for_load_state('networkidle', timeout=1000)
                    network_idle_count += 1
                except PlaywrightTimeoutError:
                    # 네트워크 활동이 있음
                    last_activity_time = current_time
                    network_idle_count = 0
                
                # 완료 조건 확인
                idle_time = current_time - last_activity_time
                if (idle_time > strategy.activity_timeout and 
                    network_idle_count >= 3 and 
                    content_size['readyState'] == 'complete'):
                    
                    elapsed = current_time - start_time
                    logger.info(f"✅ 로딩 완료: {elapsed:.1f}s, 크기: {content_size['htmlSize']/1024:.1f}KB")
                    break
                
                # 상태 로깅
                if int(current_time) % 5 == 0:  # 5초마다
                    elapsed = current_time - start_time
                    logger.debug(f"⏳ 로딩 중: {elapsed:.0f}s, 유휴: {idle_time:.1f}s, 크기: {content_size['htmlSize']/1024:.0f}KB")
                
                await asyncio.sleep(1)  # 1초 간격으로 체크
                
            except Exception as e:
                logger.debug(f"활동 모니터링 중 오류: {e}")
                await asyncio.sleep(1)
                
        total_time = time.time() - start_time
        logger.info(f"🏁 활동 기반 로딩 완료: {total_time:.1f}s")
    
    async def _handle_infinite_scroll(self, page: Page) -> None:
        """무한스크롤 처리"""
        try:
            # 스크롤 다운을 몇 번 시도
            for i in range(3):
                # 현재 페이지 높이 가져오기
                previous_height = await page.evaluate("document.body.scrollHeight")
                
                # 페이지 끝까지 스크롤
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                
                # 새 콘텐츠 로딩 대기
                await page.wait_for_timeout(1500)
                
                # 새로운 높이 확인
                new_height = await page.evaluate("document.body.scrollHeight")
                
                # 더 이상 로드할 콘텐츠가 없으면 중단
                if new_height == previous_height:
                    break
                    
                logger.info(f"🎭 스크롤 진행 중: {i+1}/3 (높이: {previous_height} → {new_height})")
            
            # 맨 위로 스크롤
            await page.evaluate("window.scrollTo(0, 0)")
            await page.wait_for_timeout(500)
            
        except Exception as e:
            logger.warning(f"무한스크롤 처리 중 오류: {e}")
    
    async def _extract_content(self, page: Page, url: str) -> Dict[str, Any]:
        """페이지에서 콘텐츠 추출"""
        try:
            # 기본 메타데이터 추출
            title = await page.title()
            
            # 메타 태그 정보 추출 (타임아웃 방지)
            try:
                meta_description = await page.get_attribute('meta[name="description"]', 'content', timeout=5000) or ""
            except:
                meta_description = ""
                
            try:
                meta_keywords = await page.get_attribute('meta[name="keywords"]', 'content', timeout=5000) or ""
            except:
                meta_keywords = ""
                
            try:
                og_title = await page.get_attribute('meta[property="og:title"]', 'content', timeout=5000) or ""
            except:
                og_title = ""
                
            try:
                og_description = await page.get_attribute('meta[property="og:description"]', 'content', timeout=5000) or ""
            except:
                og_description = ""
            
            # HTML 콘텐츠 추출
            html_content = await page.content()
            
            # 메인 콘텐츠 추출 (여러 선택자 시도)
            main_content_selectors = [
                'main',
                'article', 
                '.content',
                '.main-content',
                '.post-content',
                '.entry-content',
                '[role="main"]',
                'body'  # 마지막 옵션
            ]
            
            main_text = ""
            for selector in main_content_selectors:
                try:
                    element = await page.query_selector(selector)
                    if element:
                        main_text = await element.inner_text()
                        if len(main_text.strip()) > 100:  # 충분한 텍스트가 있으면 사용
                            break
                except Exception:
                    continue
            
            # 제목 구조 추출 (마크다운 변환용)
            headings = []
            for level in range(1, 7):  # h1 to h6
                h_elements = await page.query_selector_all(f'h{level}')
                for element in h_elements:
                    text = await element.inner_text()
                    if text.strip():
                        headings.append({
                            'level': level,
                            'text': text.strip()
                        })
            
            # 마크다운 형식으로 변환
            markdown_content = self._convert_to_markdown(title, main_text, headings)
            
            return {
                'title': title,
                'html': html_content,
                'text': main_text,
                'markdown': markdown_content,
                'metadata': {
                    'title': title,
                    'description': meta_description,
                    'keywords': meta_keywords,
                    'og_title': og_title,
                    'og_description': og_description,
                    'url': url
                },
                'headings': headings
            }
            
        except Exception as e:
            logger.error(f"콘텐츠 추출 중 오류: {e}")
            raise
    
    def _convert_to_markdown(self, title: str, text: str, headings: List[Dict]) -> str:
        """텍스트를 마크다운 형식으로 변환"""
        markdown_lines = []
        
        # 제목 추가
        if title:
            markdown_lines.append(f"# {title}\n")
        
        # 헤딩 구조를 기반으로 마크다운 생성
        if headings:
            current_text = text
            for heading in headings:
                level = heading['level']
                heading_text = heading['text']
                markdown_prefix = '#' * level
                markdown_lines.append(f"{markdown_prefix} {heading_text}\n")
        else:
            # 헤딩이 없으면 텍스트를 단락으로 분할
            paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
            for para in paragraphs:
                if len(para) > 20:  # 충분한 길이의 단락만 포함
                    markdown_lines.append(f"{para}\n")
        
        return '\n'.join(markdown_lines)
    
    def _extract_hierarchy_from_headings(self, headings: List[Dict], url: str) -> Dict[str, Any]:
        """헤딩 리스트에서 계층구조 추출"""
        hierarchy = {"depth1": "웹페이지", "depth2": {}, "depth3": {}}
        
        if not headings:
            return hierarchy
        
        current_h1 = None
        current_h2 = None
        
        for heading in headings:
            level = heading['level']
            text = heading['text']
            
            if level == 1:
                current_h1 = text
                hierarchy["depth1"] = current_h1
                if current_h1 not in hierarchy["depth2"]:
                    hierarchy["depth2"][current_h1] = []
                    
            elif level == 2:
                current_h2 = text
                if current_h1:
                    if current_h1 not in hierarchy["depth2"]:
                        hierarchy["depth2"][current_h1] = []
                    hierarchy["depth2"][current_h1].append(current_h2)
                else:
                    hierarchy["depth2"]["기타"] = hierarchy["depth2"].get("기타", [])
                    hierarchy["depth2"]["기타"].append(current_h2)
                    
            elif level == 3:
                depth3_key = current_h2 or current_h1 or "기타"
                if depth3_key not in hierarchy["depth3"]:
                    hierarchy["depth3"][depth3_key] = []
                hierarchy["depth3"][depth3_key].append(text)
        
        return hierarchy
    
    def _calculate_quality_score(self, content_data: Dict, strategy: CrawlStrategy) -> float:
        """크롤링 결과 품질 점수 계산"""
        score = 45  # Playwright 기본 점수 (브라우저 기반)
        
        # 텍스트 길이 점수 (0-25점)
        text_length = len(content_data.get('text', ''))
        if text_length > 5000:
            score += 25
        elif text_length > 2000:
            score += 20
        elif text_length > 500:
            score += 15
        elif text_length > 100:
            score += 10
        
        # 구조적 요소 점수 (0-15점)
        headings = content_data.get('headings', [])
        if headings:
            score += min(len(headings) * 2, 10)  # 헤딩 개수에 따른 점수
            h1_count = sum(1 for h in headings if h['level'] == 1)
            if h1_count > 0:
                score += 5
        
        # 메타데이터 품질 (0-10점)
        metadata = content_data.get('metadata', {})
        if metadata.get('title'):
            score += 3
        if metadata.get('description'):
            score += 3
        if metadata.get('og_title') or metadata.get('og_description'):
            score += 2
        if metadata.get('keywords'):
            score += 2
        
        # JavaScript 렌더링 보너스 (0-5점)
        score += 5  # Playwright는 항상 JS 렌더링
        
        return min(score, 100.0)
    
    async def crawl(self, url: str, strategy: CrawlStrategy) -> CrawlResult:
        """Playwright를 사용한 웹페이지 크롤링"""
        if not self.is_initialized or not self.context:
            raise RuntimeError("Playwright 엔진이 초기화되지 않았습니다")
        
        logger.info(f"🎭 Playwright로 크롤링 시작: {url}")
        
        page = None
        try:
            # 새 페이지 생성
            page = await self.context.new_page()
            
            # 페이지 이벤트 리스너 설정 (선택적)
            if strategy.anti_bot_mode:
                # 안티봇 모드에서는 더 자연스러운 행동 시뮬레이션
                await page.set_extra_http_headers({
                    'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120"',
                    'sec-ch-ua-mobile': '?0',
                    'sec-ch-ua-platform': '"macOS"',
                    'sec-fetch-dest': 'document',
                    'sec-fetch-mode': 'navigate',
                    'sec-fetch-site': 'none',
                    'sec-fetch-user': '?1',
                })
            
            # 페이지 로드
            logger.info(f"🎭 페이지 로드 중: {url}")
            await page.goto(url, timeout=strategy.timeout * 1000, wait_until='domcontentloaded')
            
            # 콘텐츠 로딩 대기
            await self._wait_for_content_load(page, strategy)
            
            # 무한스크롤 처리 (필요한 경우)
            if hasattr(strategy, 'handle_infinite_scroll') and strategy.handle_infinite_scroll:
                await self._handle_infinite_scroll(page)
            
            # 콘텐츠 추출
            content_data = await self._extract_content(page, url)
            
            # 계층구조 추출
            hierarchy = self._extract_hierarchy_from_headings(content_data.get('headings', []), url)
            
            # 품질 점수 계산
            quality_score = self._calculate_quality_score(content_data, strategy)
            
            # 결과 객체 생성
            crawl_result = CrawlResult(
                url=url,
                title=content_data['title'],
                text=content_data['markdown'],
                hierarchy=hierarchy,
                metadata={
                    "crawler_used": "playwright",
                    "processing_time": f"{strategy.timeout}s",
                    "content_quality": "high" if quality_score > 80 else "medium" if quality_score > 60 else "low",
                    "extraction_confidence": quality_score / 100,
                    "playwright_metadata": content_data['metadata'],
                    "html_length": len(content_data['html']),
                    "markdown_length": len(content_data['markdown']),
                    "text_length": len(content_data['text']),
                    "headings_count": len(content_data.get('headings', [])),
                    "quality_score": quality_score,
                    "javascript_rendered": True,
                    "anti_bot_mode": strategy.anti_bot_mode
                },
                status="complete",
                timestamp=datetime.now()
            )
            
            logger.info(f"✅ Playwright 크롤링 성공: {url} (품질: {quality_score:.1f}/100)")
            return crawl_result
            
        except PlaywrightTimeoutError as e:
            logger.error(f"❌ Playwright 크롤링 타임아웃: {url} - {e}")
            return CrawlResult(
                url=url,
                title="",
                text="",
                hierarchy={},
                metadata={
                    "crawler_used": "playwright",
                    "error_type": "TimeoutError",
                    "processing_time": "0s"
                },
                status="failed",
                timestamp=datetime.now(),
                error=f"페이지 로드 타임아웃: {str(e)}"
            )
            
        except Exception as e:
            logger.error(f"❌ Playwright 크롤링 실패: {url} - {e}")
            return CrawlResult(
                url=url,
                title="",
                text="",
                hierarchy={},
                metadata={
                    "crawler_used": "playwright",
                    "error_type": type(e).__name__,
                    "processing_time": "0s"
                },
                status="failed",
                timestamp=datetime.now(),
                error=str(e)
            )
        finally:
            # 페이지 정리
            if page:
                try:
                    await page.close()
                except Exception:
                    pass 