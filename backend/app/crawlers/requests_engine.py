import logging
import asyncio
import aiohttp
from typing import Dict, Any
from datetime import datetime
from urllib.parse import urljoin, urlparse
import re

from .base import BaseCrawler, CrawlResult, CrawlStrategy, EngineCapabilities

logger = logging.getLogger(__name__)

try:
    from bs4 import BeautifulSoup
    BS4_AVAILABLE = True
except ImportError:
    BS4_AVAILABLE = False
    logger.warning("BeautifulSoup4 라이브러리가 설치되지 않았습니다")

class RequestsEngine(BaseCrawler):
    """Requests + BeautifulSoup 기반 빠른 크롤링 엔진"""
    
    def __init__(self):
        super().__init__("requests")
        self.session = None
    
    async def initialize(self) -> None:
        """HTTP 세션 초기화"""
        if not BS4_AVAILABLE:
            raise RuntimeError("BeautifulSoup4 라이브러리가 설치되지 않았습니다")
        
        # aiohttp 세션 생성
        timeout = aiohttp.ClientTimeout(total=30)
        self.session = aiohttp.ClientSession(
            timeout=timeout,
            headers={
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            }
        )
        
        self.is_initialized = True
        logger.info("🌐 Requests 엔진 초기화 완료")
    
    async def cleanup(self) -> None:
        """HTTP 세션 정리"""
        if self.session:
            await self.session.close()
        self.session = None
        self.is_initialized = False
        logger.info("🌐 Requests 엔진 정리 완료")
    
    def get_capabilities(self) -> Dict[str, Any]:
        """Requests 엔진의 능력"""
        return {
            EngineCapabilities.JAVASCRIPT_RENDERING: False,
            EngineCapabilities.ANTI_BOT_BYPASS: False,
            EngineCapabilities.FAST_STATIC: True,
            EngineCapabilities.BULK_PROCESSING: True,
            "supported_formats": ["html", "text"],
            "rate_limits": "매우 낮음 (직접 HTTP 요청)",
            "best_for": ["정적 HTML", "빠른 처리", "대량 크롤링", "API 엔드포인트"]
        }
    
    def _extract_text_content(self, soup: BeautifulSoup) -> str:
        """HTML에서 텍스트 내용 추출"""
        # 불필요한 태그 제거
        for tag in soup(["script", "style", "nav", "header", "footer", "aside", "advertisement"]):
            tag.decompose()
        
        # 주요 콘텐츠 영역 찾기
        main_content = soup.find('main') or soup.find('article') or soup.find('div', class_=re.compile(r'content|main|article|post'))
        
        if main_content:
            text = main_content.get_text(separator='\n', strip=True)
        else:
            text = soup.get_text(separator='\n', strip=True)
        
        # 텍스트 정리
        lines = text.split('\n')
        cleaned_lines = []
        
        for line in lines:
            line = line.strip()
            if line and len(line) > 2:  # 너무 짧은 줄 제외
                cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines)
    
    def _extract_hierarchy_from_html(self, soup: BeautifulSoup, url: str) -> Dict[str, Any]:
        """HTML에서 계층구조 추출"""
        hierarchy = {"depth1": "웹페이지", "depth2": {}, "depth3": {}}
        
        # 페이지 제목을 depth1으로 사용
        title_tag = soup.find('title')
        if title_tag:
            hierarchy["depth1"] = title_tag.get_text().strip()
        
        # 헤더 태그들에서 계층구조 추출
        headers = soup.find_all(['h1', 'h2', 'h3', 'h4'])
        
        current_h1 = None
        current_h2 = None
        
        for header in headers:
            text = header.get_text().strip()
            if not text:
                continue
            
            if header.name == 'h1':
                current_h1 = text
                if current_h1 not in hierarchy["depth2"]:
                    hierarchy["depth2"][current_h1] = []
                    
            elif header.name == 'h2':
                current_h2 = text
                if current_h1:
                    hierarchy["depth2"][current_h1].append(current_h2)
                else:
                    hierarchy["depth2"]["기타"] = hierarchy["depth2"].get("기타", [])
                    hierarchy["depth2"]["기타"].append(current_h2)
                    
            elif header.name in ['h3', 'h4']:
                depth3_key = current_h2 or current_h1 or "기타"
                if depth3_key not in hierarchy["depth3"]:
                    hierarchy["depth3"][depth3_key] = []
                hierarchy["depth3"][depth3_key].append(text)
        
        # 네비게이션 메뉴에서도 구조 추출
        nav_elements = soup.find_all(['nav', 'ul', 'ol'], class_=re.compile(r'menu|nav|navigation'))
        for nav in nav_elements:
            links = nav.find_all('a')
            if len(links) > 2:  # 의미있는 네비게이션으로 판단
                nav_items = [link.get_text().strip() for link in links if link.get_text().strip()]
                if nav_items:
                    hierarchy["depth2"]["네비게이션"] = nav_items[:10]  # 최대 10개
        
        return hierarchy
    
    def _calculate_quality_score(self, soup: BeautifulSoup, text_content: str, response_size: int) -> float:
        """크롤링 결과 품질 점수 계산"""
        score = 40  # 기본 성공 점수
        
        # 텍스트 길이 점수 (0-25점)
        text_length = len(text_content)
        if text_length > 3000:
            score += 25
        elif text_length > 1000:
            score += 15
        elif text_length > 300:
            score += 10
        elif text_length > 50:
            score += 5
        
        # HTML 구조 점수 (0-20점)
        structure_score = 0
        if soup.find('title'):
            structure_score += 3
        if soup.find_all(['h1', 'h2', 'h3']):
            structure_score += 5
        if soup.find_all('p'):
            structure_score += 4
        if soup.find_all('a'):
            structure_score += 3
        if soup.find(['main', 'article', 'section']):
            structure_score += 5
        score += structure_score
        
        # 메타데이터 점수 (0-10점)
        meta_score = 0
        if soup.find('meta', attrs={'name': 'description'}):
            meta_score += 3
        if soup.find('meta', attrs={'name': 'keywords'}):
            meta_score += 2
        if soup.find('meta', attrs={'property': 'og:title'}):
            meta_score += 2
        if soup.find('meta', attrs={'property': 'og:description'}):
            meta_score += 3
        score += meta_score
        
        # 응답 크기 점수 (0-5점)
        if response_size > 10000:
            score += 5
        elif response_size > 5000:
            score += 3
        elif response_size > 1000:
            score += 1
        
        return min(score, 100.0)
    
    async def _read_response_with_activity_timeout(self, response, activity_timeout: int, 
                                                  max_total_time: int, url: str) -> bytes:
        """
        활동 기반 응답 읽기 - 단순화된 버전
        """
        import time
        
        content_chunks = []
        total_size = 0
        start_time = time.time()
        last_chunk_time = start_time
        
        logger.info(f"📡 활동 기반 읽기 시작: {url} (활동타임아웃: {activity_timeout}s, 최대: {max_total_time}s)")
        
        try:
            # 청크 단위로 읽기 (한 번만!)
            async for chunk in response.content.iter_chunked(8192):  # 8KB 청크
                if not chunk:
                    break
                    
                content_chunks.append(chunk)
                total_size += len(chunk)
                last_chunk_time = time.time()
                
                # 진행 상황 로깅 (500KB마다)
                if total_size % (500 * 1024) < 8192:  # 청크 크기 고려
                    elapsed = time.time() - start_time
                    logger.info(f"📊 읽기 진행중: {total_size/1024:.0f}KB ({elapsed:.1f}s 경과)")
                
                # 최대 총 시간 초과 체크 (안전장치)
                if time.time() - start_time > max_total_time:
                    logger.warning(f"⚠️ 최대 총 시간 초과 ({max_total_time}s), 현재까지 읽은 데이터 반환")
                    break
                    
                # 청크 간 간격이 너무 길면 중단
                time_since_last_chunk = time.time() - last_chunk_time
                if time_since_last_chunk > activity_timeout:
                    logger.warning(f"⚠️ 청크 간 간격 초과 ({time_since_last_chunk:.1f}s > {activity_timeout}s)")
                    break
            
            # 완료
            total_time = time.time() - start_time
            logger.info(f"✅ 활동 기반 읽기 완료: {total_size/1024:.1f}KB, {total_time:.1f}s 소요")
            
            return b''.join(content_chunks)
            
        except Exception as e:
            total_time = time.time() - start_time  
            logger.error(f"❌ 활동 기반 읽기 실패: {e} ({total_time:.1f}s 경과, {total_size/1024:.1f}KB 읽음)")
            
            # 부분적으로라도 읽은 데이터가 있으면 반환
            if content_chunks:
                logger.info(f"🔄 부분 데이터 반환: {total_size/1024:.1f}KB")
                return b''.join(content_chunks)
            else:
                raise
    
    async def crawl(self, url: str, strategy: CrawlStrategy) -> CrawlResult:
        """Requests를 사용한 웹페이지 크롤링 (활동 기반 타임아웃)"""
        if not self.is_initialized or not self.session:
            raise RuntimeError("Requests 엔진이 초기화되지 않았습니다")
        
        logger.info(f"🌐 Requests로 크롤링 시작: {url}")
        
        try:
            # 초기 연결 타임아웃 (빠르게)
            connector_timeout = aiohttp.ClientTimeout(total=strategy.timeout, connect=10)
            
            async with self.session.get(url, timeout=connector_timeout) as response:
                # 상태 코드 확인
                if response.status >= 400:
                    raise Exception(f"HTTP {response.status}: {response.reason}")
                
                # Content-Type 확인
                content_type = response.headers.get('content-type', '').lower()
                if 'text/html' not in content_type and 'application/xml' not in content_type:
                    logger.warning(f"⚠️ 예상치 못한 Content-Type: {content_type}")
                
                # 🔥 활동 기반 스트리밍 읽기
                content = await self._read_response_with_activity_timeout(
                    response, strategy.activity_timeout, strategy.max_total_time, url
                )
                
                # 인코딩 처리
                encoding = response.charset or 'utf-8'
                try:
                    html_content = content.decode(encoding)
                except UnicodeDecodeError:
                    html_content = content.decode('utf-8', errors='ignore')
                
                # BeautifulSoup로 파싱
                soup = BeautifulSoup(html_content, 'html.parser')
                
                # 제목 추출
                title_tag = soup.find('title')
                title = title_tag.get_text().strip() if title_tag else "제목 없음"
                
                # 텍스트 내용 추출
                text_content = self._extract_text_content(soup)
                
                # 계층구조 추출
                hierarchy = self._extract_hierarchy_from_html(soup, url)
                
                # 품질 점수 계산
                quality_score = self._calculate_quality_score(soup, text_content, len(content))
                
                # 메타데이터 수집
                meta_description = soup.find('meta', attrs={'name': 'description'})
                meta_keywords = soup.find('meta', attrs={'name': 'keywords'})
                og_title = soup.find('meta', attrs={'property': 'og:title'})
                og_description = soup.find('meta', attrs={'property': 'og:description'})
                
                # 결과 객체 생성
                crawl_result = CrawlResult(
                    url=url,
                    title=title,
                    text=text_content,
                    hierarchy=hierarchy,
                    metadata={
                        "crawler_used": "requests",
                        "processing_time": "활동기반",
                        "content_quality": "high" if quality_score > 80 else "medium" if quality_score > 50 else "low",
                        "extraction_confidence": quality_score / 100,
                        "http_status": response.status,
                        "content_type": content_type,
                        "content_length": len(content),
                        "text_length": len(text_content),
                        "quality_score": quality_score,
                        "timeout_strategy": "activity_based",
                        "meta_description": meta_description.get('content') if meta_description else None,
                        "meta_keywords": meta_keywords.get('content') if meta_keywords else None,
                        "og_title": og_title.get('content') if og_title else None,
                        "og_description": og_description.get('content') if og_description else None,
                    },
                    status="complete",
                    timestamp=datetime.now()
                )
                
                logger.info(f"✅ Requests 크롤링 성공: {url} (품질: {quality_score:.1f}/100, 크기: {len(content)/1024:.1f}KB)")
                return crawl_result
                
        except asyncio.TimeoutError:
            error_msg = f"연결 시간 초과 ({strategy.timeout}초)"
            logger.error(f"⏰ {error_msg}: {url}")
        except Exception as e:
            error_msg = str(e)
            logger.error(f"❌ Requests 크롤링 실패: {url} - {error_msg}")
        
        # 실패 시 결과
        return CrawlResult(
            url=url,
            title="",
            text="",
            hierarchy={},
            metadata={
                "crawler_used": "requests",
                "error_type": type(e).__name__ if 'e' in locals() else "TimeoutError",
                "processing_time": "0s"
            },
            status="failed",
            timestamp=datetime.now(),
            error=error_msg if 'error_msg' in locals() else "알 수 없는 오류"
        ) 