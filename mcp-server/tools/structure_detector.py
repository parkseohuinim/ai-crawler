"""
콘텐츠 구조 패턴 분석 도구
계층구조 식별, 주요 콘텐츠 영역 감지, 네비게이션/사이드바 구분
"""

import re
import logging
from typing import Dict, Optional, List, Tuple
from bs4 import BeautifulSoup, Tag
from collections import Counter

logger = logging.getLogger(__name__)

class StructureDetector:
    """콘텐츠 구조 패턴 분석"""
    
    def __init__(self):
        # 주요 콘텐츠 영역 식별을 위한 CSS 선택자들
        self.content_selectors = [
            'main', 'article', '.content', '.main', '.post', '.entry',
            '#content', '#main', '.container', '.wrapper', '.page-content'
        ]
        
        # 네비게이션 식별 선택자들
        self.nav_selectors = [
            'nav', 'navigation', '.nav', '.menu', '.navbar', 
            '#nav', '#menu', '.header-menu', '.main-menu'
        ]
        
        # 사이드바 식별 선택자들
        self.sidebar_selectors = [
            'aside', '.sidebar', '.side', '.widget', '.secondary',
            '#sidebar', '.right-sidebar', '.left-sidebar'
        ]
    
    async def detect_structure(self, html_sample: str, url: Optional[str] = None) -> Dict:
        """
        콘텐츠 구조 패턴 분석
        
        Args:
            html_sample: 분석할 HTML 샘플
            url: 원본 URL (선택사항)
            
        Returns:
            구조 분석 결과
        """
        try:
            logger.info(f"콘텐츠 구조 분석 시작: {url or 'Unknown URL'}")
            
            soup = BeautifulSoup(html_sample, 'html.parser')
            
            # 기본 구조 분석
            structure_results = {
                "url": url,
                "hierarchy": await self._analyze_heading_hierarchy(soup),
                "content_areas": await self._identify_content_areas(soup),
                "navigation": await self._analyze_navigation(soup),
                "layout_type": await self._detect_layout_type(soup),
                "semantic_structure": await self._analyze_semantic_elements(soup),
                "data_extraction_hints": await self._generate_extraction_hints(soup),
                "content_density": await self._calculate_content_density(soup)
            }
            
            logger.info("콘텐츠 구조 분석 완료")
            return structure_results
            
        except Exception as e:
            logger.error(f"구조 분석 오류: {e}")
            return {
                "url": url,
                "error": str(e),
                "hierarchy": {"levels": 0},
                "content_areas": [],
                "layout_type": "unknown"
            }
    
    async def _analyze_heading_hierarchy(self, soup: BeautifulSoup) -> Dict:
        """제목 계층구조 분석"""
        
        headings = {}
        heading_order = []
        
        for level in range(1, 7):  # h1~h6
            tags = soup.find_all(f'h{level}')
            if tags:
                headings[f'h{level}'] = []
                for tag in tags:
                    text = tag.get_text().strip()
                    if text:
                        headings[f'h{level}'].append({
                            "text": text,
                            "position": len(heading_order),
                            "classes": tag.get('class', []),
                            "id": tag.get('id', '')
                        })
                        heading_order.append((f'h{level}', text))
        
        # 계층구조 품질 평가
        hierarchy_quality = self._evaluate_hierarchy_quality(headings)
        
        return {
            "headings": headings,
            "order": heading_order,
            "levels": len(headings),
            "total_headings": len(heading_order),
            "quality": hierarchy_quality,
            "main_topics": self._extract_main_topics(headings)
        }
    
    async def _identify_content_areas(self, soup: BeautifulSoup) -> List[Dict]:
        """주요 콘텐츠 영역 식별"""
        
        content_areas = []
        
        # 의미론적 HTML5 태그들 우선 검사
        semantic_areas = soup.find_all(['main', 'article', 'section', 'aside', 'header', 'footer'])
        
        for area in semantic_areas:
            text_content = area.get_text().strip()
            if len(text_content) > 100:  # 최소 콘텐츠 길이
                content_areas.append({
                    "type": area.name,
                    "selector": area.name,
                    "text_length": len(text_content),
                    "element_count": len(area.find_all()),
                    "classes": area.get('class', []),
                    "id": area.get('id', ''),
                    "confidence": 0.9  # 의미론적 태그는 높은 신뢰도
                })
        
        # CSS 클래스 기반 콘텐츠 영역 탐지
        for selector in self.content_selectors:
            elements = soup.select(selector)
            for elem in elements:
                text_content = elem.get_text().strip()
                if len(text_content) > 200:
                    content_areas.append({
                        "type": "content",
                        "selector": selector,
                        "text_length": len(text_content),
                        "element_count": len(elem.find_all()),
                        "classes": elem.get('class', []),
                        "id": elem.get('id', ''),
                        "confidence": 0.7
                    })
        
        # 중복 제거 및 정렬
        content_areas = self._deduplicate_areas(content_areas)
        content_areas.sort(key=lambda x: x['text_length'], reverse=True)
        
        return content_areas[:10]  # 상위 10개만 반환
    
    async def _analyze_navigation(self, soup: BeautifulSoup) -> Dict:
        """네비게이션 구조 분석"""
        
        nav_elements = []
        
        # 네비게이션 요소들 찾기
        for selector in self.nav_selectors:
            elements = soup.select(selector)
            for elem in elements:
                links = elem.find_all('a')
                if links:
                    nav_elements.append({
                        "selector": selector,
                        "link_count": len(links),
                        "text": elem.get_text().strip()[:200],
                        "classes": elem.get('class', []),
                        "id": elem.get('id', ''),
                        "links": [{"text": a.get_text().strip(), "href": a.get('href', '')} 
                                for a in links[:20]]  # 최대 20개 링크
                    })
        
        # 메뉴 타입 분석
        menu_types = self._classify_menu_types(nav_elements)
        
        return {
            "navigation_elements": nav_elements,
            "menu_types": menu_types,
            "total_nav_links": sum(elem['link_count'] for elem in nav_elements),
            "has_breadcrumbs": self._detect_breadcrumbs(soup),
            "has_mega_menu": any(elem['link_count'] > 20 for elem in nav_elements)
        }
    
    async def _detect_layout_type(self, soup: BeautifulSoup) -> Dict:
        """레이아웃 타입 감지"""
        
        # 주요 레이아웃 컨테이너들
        containers = soup.find_all(['div', 'section', 'main'], 
                                 class_=re.compile(r'container|wrapper|grid|flex', re.I))
        
        # 그리드/플렉스 레이아웃 감지
        has_grid = bool(soup.find_all(class_=re.compile(r'grid|col-', re.I)))
        has_flex = bool(soup.find_all(class_=re.compile(r'flex|d-flex', re.I)))
        
        # 컬럼 레이아웃 감지
        columns = self._detect_column_layout(soup)
        
        # 반응형 디자인 감지
        responsive = self._detect_responsive_design(soup)
        
        layout_type = "unknown"
        if columns >= 3:
            layout_type = "multi_column"
        elif columns == 2:
            layout_type = "two_column"
        elif has_grid or has_flex:
            layout_type = "modern_layout"
        else:
            layout_type = "single_column"
        
        return {
            "type": layout_type,
            "columns": columns,
            "has_grid": has_grid,
            "has_flex": has_flex,
            "responsive": responsive,
            "containers": len(containers)
        }
    
    async def _analyze_semantic_elements(self, soup: BeautifulSoup) -> Dict:
        """의미론적 HTML5 요소 분석"""
        
        semantic_tags = ['header', 'nav', 'main', 'article', 'section', 
                        'aside', 'footer', 'figure', 'figcaption', 'time']
        
        semantic_structure = {}
        for tag in semantic_tags:
            elements = soup.find_all(tag)
            if elements:
                semantic_structure[tag] = {
                    "count": len(elements),
                    "has_content": any(elem.get_text().strip() for elem in elements)
                }
        
        # 구조화된 데이터 감지
        structured_data = {
            "json_ld": len(soup.find_all('script', type='application/ld+json')),
            "microdata": len(soup.find_all(attrs={'itemscope': True})),
            "rdfa": len(soup.find_all(attrs={'property': re.compile(r'.+')}))
        }
        
        return {
            "semantic_tags": semantic_structure,
            "structured_data": structured_data,
            "semantic_score": len(semantic_structure) / len(semantic_tags) * 100
        }
    
    async def _generate_extraction_hints(self, soup: BeautifulSoup) -> Dict:
        """데이터 추출을 위한 힌트 생성"""
        
        # 주요 콘텐츠 선택자 추천
        content_selectors = []
        if soup.find('main'):
            content_selectors.append('main')
        if soup.find('article'):
            content_selectors.append('article')
        if soup.select('.content'):
            content_selectors.append('.content')
        
        # 제목 추출 선택자
        title_selectors = []
        if soup.find('h1'):
            title_selectors.append('h1')
        if soup.select('.title'):
            title_selectors.append('.title')
        
        # 메타데이터 추출 힌트
        metadata_hints = {
            "has_timestamps": bool(soup.find_all('time')),
            "has_authors": bool(soup.find_all(class_=re.compile(r'author|byline', re.I))),
            "has_tags": bool(soup.find_all(class_=re.compile(r'tag|category', re.I))),
            "has_social": bool(soup.find_all(class_=re.compile(r'social|share', re.I)))
        }
        
        return {
            "content_selectors": content_selectors,
            "title_selectors": title_selectors,
            "metadata_hints": metadata_hints,
            "exclude_selectors": ['.advertisement', '.ads', '.sidebar', 'nav', 'footer'],
            "priority_order": ['main', 'article', '.content', 'section']
        }
    
    async def _calculate_content_density(self, soup: BeautifulSoup) -> Dict:
        """콘텐츠 밀도 계산"""
        
        total_text = soup.get_text()
        total_html = str(soup)
        
        # 텍스트 대비 HTML 비율
        text_ratio = len(total_text) / max(len(total_html), 1)
        
        # 단락 수
        paragraphs = len(soup.find_all('p'))
        
        # 링크 밀도
        links = len(soup.find_all('a'))
        link_density = links / max(len(total_text.split()), 1) * 100
        
        return {
            "text_to_html_ratio": text_ratio,
            "paragraph_count": paragraphs,
            "link_count": links,
            "link_density": link_density,
            "content_quality": "high" if text_ratio > 0.2 and paragraphs > 5 else "medium" if text_ratio > 0.1 else "low"
        }
    
    def _evaluate_hierarchy_quality(self, headings: Dict) -> str:
        """제목 계층구조 품질 평가"""
        if not headings:
            return "none"
        
        has_h1 = 'h1' in headings
        level_count = len(headings)
        
        if has_h1 and level_count >= 3:
            return "excellent"
        elif has_h1 and level_count >= 2:
            return "good"
        elif level_count >= 2:
            return "fair"
        else:
            return "poor"
    
    def _extract_main_topics(self, headings: Dict) -> List[str]:
        """주요 토픽 추출"""
        main_topics = []
        
        # H1 태그에서 주요 토픽
        if 'h1' in headings:
            main_topics.extend([h['text'] for h in headings['h1']])
        
        # H2 태그에서 섹션 토픽
        if 'h2' in headings:
            main_topics.extend([h['text'] for h in headings['h2'][:5]])  # 최대 5개
        
        return main_topics
    
    def _classify_menu_types(self, nav_elements: List[Dict]) -> List[str]:
        """메뉴 타입 분류"""
        menu_types = []
        
        for nav in nav_elements:
            if 'breadcrumb' in ' '.join(nav['classes']).lower():
                menu_types.append('breadcrumb')
            elif nav['link_count'] > 20:
                menu_types.append('mega_menu')
            elif 'footer' in nav['selector']:
                menu_types.append('footer_menu')
            elif 'main' in nav['selector'] or 'primary' in ' '.join(nav['classes']).lower():
                menu_types.append('main_menu')
            else:
                menu_types.append('secondary_menu')
        
        return list(set(menu_types))
    
    def _detect_breadcrumbs(self, soup: BeautifulSoup) -> bool:
        """브레드크럼 감지"""
        breadcrumb_selectors = [
            '.breadcrumb', '.breadcrumbs', '[aria-label*="breadcrumb"]',
            '.crumbs', '.path', '.navigation-path'
        ]
        
        return any(soup.select(selector) for selector in breadcrumb_selectors)
    
    def _detect_column_layout(self, soup: BeautifulSoup) -> int:
        """컬럼 레이아웃 감지"""
        # CSS 클래스 기반 컬럼 감지
        col_patterns = [
            r'col-\d+', r'column-\d+', r'grid-\d+', 
            r'span-\d+', r'w-\d+', r'width-\d+'
        ]
        
        max_columns = 1
        for pattern in col_patterns:
            matches = soup.find_all(class_=re.compile(pattern, re.I))
            if matches:
                # 숫자 추출해서 최대값 찾기
                for match in matches:
                    classes = ' '.join(match.get('class', []))
                    numbers = re.findall(r'\d+', classes)
                    if numbers:
                        max_columns = max(max_columns, max(int(n) for n in numbers if int(n) <= 12))
        
        return min(max_columns, 12)  # 최대 12컬럼으로 제한
    
    def _detect_responsive_design(self, soup: BeautifulSoup) -> bool:
        """반응형 디자인 감지"""
        # 뷰포트 메타태그 확인
        viewport = soup.find('meta', attrs={'name': 'viewport'})
        if viewport:
            return True
        
        # 반응형 CSS 클래스 확인
        responsive_classes = [
            'responsive', 'mobile', 'tablet', 'desktop',
            'sm-', 'md-', 'lg-', 'xl-', 'hidden-', 'visible-'
        ]
        
        for class_pattern in responsive_classes:
            if soup.find(class_=re.compile(class_pattern, re.I)):
                return True
        
        return False
    
    def _deduplicate_areas(self, areas: List[Dict]) -> List[Dict]:
        """중복 영역 제거"""
        unique_areas = []
        seen_selectors = set()
        
        for area in areas:
            key = (area['selector'], area['text_length'])
            if key not in seen_selectors:
                seen_selectors.add(key)
                unique_areas.append(area)
        
        return unique_areas 