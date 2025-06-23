"""
선택적 콘텐츠 추출 도구
특정 부분만 타겟팅하여 추출하는 AI 기반 도구
"""

import re
import logging
from typing import Dict, Any, Optional, List
from bs4 import BeautifulSoup
import asyncio

logger = logging.getLogger(__name__)

class ContentExtractor:
    """AI 기반 선택적 콘텐츠 추출기"""
    
    def __init__(self):
        # 콘텐츠 타입별 추출 전략
        self.extraction_strategies = {
            "제목": self._extract_title,
            "가격": self._extract_price,
            "본문": self._extract_main_content,
            "리뷰": self._extract_reviews,
            "요약": self._extract_summary,
            "이미지": self._extract_images,
            "링크": self._extract_links,
            "날짜": self._extract_date
        }
    
    async def extract_selective_content(
        self, 
        html_content: str, 
        target_content: str, 
        url: str = ""
    ) -> Dict[str, Any]:
        """
        선택적 콘텐츠 추출
        
        Args:
            html_content: HTML 내용 또는 마크다운 텍스트
            target_content: 추출할 콘텐츠 타입 ("제목", "가격" 등)
            url: 원본 URL (컨텍스트 용)
            
        Returns:
            추출된 데이터 및 메타정보
        """
        try:
            logger.info(f"🎯 선택적 추출 시작: {target_content} from {url}")
            
            # HTML 파싱
            if html_content.startswith('<'):
                soup = BeautifulSoup(html_content, 'html.parser')
                is_html = True
            else:
                # 마크다운이나 플레인 텍스트
                soup = None
                is_html = False
            
            # 전략에 따른 추출 실행
            extraction_func = self.extraction_strategies.get(
                target_content, 
                self._extract_fallback
            )
            
            if is_html and soup:
                extracted_data = await extraction_func(soup, html_content, url)
            else:
                extracted_data = await self._extract_from_text(
                    html_content, target_content, url
                )
            
            # 결과 검증 및 품질 평가
            quality_score = self._calculate_extraction_quality(
                extracted_data, target_content
            )
            
            result = {
                "target_content": target_content,
                "extracted_data": extracted_data,
                "url": url,
                "extraction_method": "html" if is_html else "text",
                "quality_score": quality_score,
                "metadata": {
                    "extraction_time": "fast",
                    "confidence": self._calculate_confidence(extracted_data),
                    "source_type": "html" if is_html else "markdown/text"
                }
            }
            
            logger.info(f"✅ 선택적 추출 완료: {target_content}, 품질: {quality_score:.1f}")
            return result
            
        except Exception as e:
            logger.error(f"❌ 선택적 추출 실패: {e}")
            return {
                "target_content": target_content,
                "extracted_data": {},
                "error": str(e),
                "url": url,
                "quality_score": 0.0
            }
    
    async def _extract_title(self, soup: BeautifulSoup, html: str, url: str) -> Dict:
        """제목 추출"""
        titles = []
        
        # HTML title 태그
        title_tag = soup.find('title')
        if title_tag:
            titles.append({
                "type": "page_title",
                "text": title_tag.get_text().strip(),
                "confidence": 0.9
            })
        
        # H1 태그들
        h1_tags = soup.find_all('h1')
        for h1 in h1_tags[:3]:  # 상위 3개만
            text = h1.get_text().strip()
            if text and len(text) > 5:
                titles.append({
                    "type": "main_heading",
                    "text": text,
                    "confidence": 0.8
                })
        
        # 메타 og:title
        og_title = soup.find('meta', property='og:title')
        if og_title and og_title.get('content'):
            titles.append({
                "type": "og_title",
                "text": og_title['content'].strip(),
                "confidence": 0.7
            })
        
        # H2 태그들 (보조 제목)
        h2_tags = soup.find_all('h2')
        for h2 in h2_tags[:2]:  # 상위 2개만
            text = h2.get_text().strip()
            if text and len(text) > 3:
                titles.append({
                    "type": "sub_heading",
                    "text": text,
                    "confidence": 0.6
                })
        
        return {
            "titles": titles,
            "primary_title": titles[0]["text"] if titles else "제목을 찾을 수 없습니다",
            "total_found": len(titles)
        }
    
    async def _extract_price(self, soup: BeautifulSoup, html: str, url: str) -> Dict:
        """가격 정보 추출"""
        prices = []
        
        # 가격 패턴들
        price_patterns = [
            r'[\₩$¥€£]\s*[\d,]+(?:\.\d{2})?',  # 통화 기호 + 숫자
            r'[\d,]+\s*[원달러유로엔円]',         # 숫자 + 통화 단위
            r'[\d,]+(?:\.\d{2})?\s*[원달러]',     # 소수점 포함
            r'price["\s:]*[\d,]+',              # price: 123456
            r'[\d,]+\s*WON',                    # 숫자 + WON
        ]
        
        # HTML 텍스트에서 가격 패턴 검색
        text_content = soup.get_text()
        
        for pattern in price_patterns:
            matches = re.findall(pattern, text_content, re.IGNORECASE)
            for match in matches:
                # 숫자 추출 및 정규화
                numbers = re.findall(r'[\d,]+', match)
                if numbers:
                    price_value = numbers[0].replace(',', '')
                    if price_value.isdigit() and len(price_value) >= 3:
                        prices.append({
                            "raw_text": match,
                            "value": int(price_value),
                            "formatted": f"{int(price_value):,}원",
                            "confidence": 0.7
                        })
        
        # 특정 클래스나 ID에서 가격 검색
        price_selectors = [
            '[class*="price"]', '[id*="price"]',
            '[class*="cost"]', '[id*="cost"]',
            '[class*="amount"]', '.money', '.currency'
        ]
        
        for selector in price_selectors:
            elements = soup.select(selector)
            for elem in elements:
                text = elem.get_text().strip()
                numbers = re.findall(r'[\d,]+', text)
                if numbers:
                    price_value = numbers[0].replace(',', '')
                    if price_value.isdigit() and len(price_value) >= 3:
                        prices.append({
                            "raw_text": text,
                            "value": int(price_value),
                            "formatted": f"{int(price_value):,}원",
                            "confidence": 0.8,
                            "source": "css_selector"
                        })
        
        # 중복 제거 및 정렬
        unique_prices = []
        seen_values = set()
        
        for price in sorted(prices, key=lambda x: x["confidence"], reverse=True):
            if price["value"] not in seen_values:
                unique_prices.append(price)
                seen_values.add(price["value"])
                
        return {
            "prices": unique_prices[:5],  # 상위 5개만
            "primary_price": unique_prices[0] if unique_prices else None,
            "total_found": len(unique_prices),
            "price_range": {
                "min": min(p["value"] for p in unique_prices) if unique_prices else 0,
                "max": max(p["value"] for p in unique_prices) if unique_prices else 0
            }
        }
    
    async def _extract_main_content(self, soup: BeautifulSoup, html: str, url: str) -> Dict:
        """본문 내용 추출"""
        content_parts = []
        
        # 주요 콘텐츠 영역 우선순위
        content_selectors = [
            'main', 'article', '[role="main"]',
            '.content', '.post-content', '.article-content',
            '.entry-content', '.post-body', '.content-body'
        ]
        
        main_content = None
        for selector in content_selectors:
            element = soup.select_one(selector)
            if element:
                main_content = element
                break
        
        if not main_content:
            # body에서 script, style 제거 후 추출
            main_content = soup.find('body') or soup
        
        # 불필요한 요소 제거
        for tag in main_content.find_all(['script', 'style', 'nav', 'header', 'footer', 'aside']):
            tag.decompose()
        
        # 문단별로 텍스트 추출
        paragraphs = main_content.find_all(['p', 'div'], string=True)
        
        for p in paragraphs:
            text = p.get_text().strip()
            if text and len(text) > 20:  # 의미있는 길이의 텍스트만
                content_parts.append({
                    "text": text,
                    "tag": p.name,
                    "length": len(text)
                })
        
        # 전체 텍스트
        full_text = main_content.get_text(separator='\n', strip=True)
        
        return {
            "paragraphs": content_parts[:10],  # 상위 10개 문단
            "full_text": full_text[:2000],  # 2000자 제한
            "total_paragraphs": len(content_parts),
            "total_length": len(full_text),
            "summary": full_text[:200] + "..." if len(full_text) > 200 else full_text
        }
    
    async def _extract_reviews(self, soup: BeautifulSoup, html: str, url: str) -> Dict:
        """리뷰 정보 추출"""
        reviews = []
        
        # 리뷰 관련 선택자들
        review_selectors = [
            '[class*="review"]', '[id*="review"]',
            '[class*="comment"]', '[id*="comment"]',
            '[class*="feedback"]', '.testimonial',
            '[data-testid*="review"]', '[role="review"]'
        ]
        
        for selector in review_selectors:
            elements = soup.select(selector)
            for elem in elements[:5]:  # 최대 5개 리뷰
                text = elem.get_text().strip()
                if text and len(text) > 10:
                    # 평점 추출 시도
                    rating_match = re.search(r'(\d+(?:\.\d+)?)\s*[/★⭐점stars]', text)
                    rating = float(rating_match.group(1)) if rating_match else None
                    
                    reviews.append({
                        "text": text[:300],  # 300자 제한
                        "rating": rating,
                        "length": len(text),
                        "confidence": 0.7
                    })
        
        # 평점 패턴 검색
        rating_patterns = [
            r'(\d+(?:\.\d+)?)\s*[/★⭐점]',
            r'(\d+(?:\.\d+)?)\s*stars?',
            r'평점[:\s]*(\d+(?:\.\d+)?)'
        ]
        
        ratings = []
        for pattern in rating_patterns:
            matches = re.findall(pattern, soup.get_text(), re.IGNORECASE)
            for match in matches:
                try:
                    rating_value = float(match)
                    if 0 <= rating_value <= 5:
                        ratings.append(rating_value)
                except ValueError:
                    continue
        
        return {
            "reviews": reviews,
            "total_reviews": len(reviews),
            "ratings": ratings,
            "average_rating": sum(ratings) / len(ratings) if ratings else None,
            "rating_count": len(ratings)
        }
    
    async def _extract_summary(self, soup: BeautifulSoup, html: str, url: str) -> Dict:
        """요약 정보 추출"""
        summary_parts = []
        
        # 메타 설명
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc and meta_desc.get('content'):
            summary_parts.append({
                "type": "meta_description",
                "text": meta_desc['content'].strip(),
                "confidence": 0.9
            })
        
        # og:description  
        og_desc = soup.find('meta', property='og:description')
        if og_desc and og_desc.get('content'):
            summary_parts.append({
                "type": "og_description", 
                "text": og_desc['content'].strip(),
                "confidence": 0.8
            })
        
        # 첫 번째 문단 (요약으로 사용)
        first_p = soup.find('p')
        if first_p:
            text = first_p.get_text().strip()
            if text and len(text) > 50:
                summary_parts.append({
                    "type": "first_paragraph",
                    "text": text,
                    "confidence": 0.6
                })
        
        # abstract나 summary 클래스
        summary_elements = soup.select('.summary, .abstract, .excerpt, .intro')
        for elem in summary_elements:
            text = elem.get_text().strip()
            if text and len(text) > 20:
                summary_parts.append({
                    "type": "summary_section",
                    "text": text,
                    "confidence": 0.7
                })
        
        return {
            "summaries": summary_parts,
            "primary_summary": summary_parts[0]["text"] if summary_parts else "요약을 찾을 수 없습니다",
            "total_found": len(summary_parts)
        }
    
    async def _extract_images(self, soup: BeautifulSoup, html: str, url: str) -> Dict:
        """이미지 정보 추출"""
        images = []
        
        # 모든 img 태그 수집
        img_tags = soup.find_all('img')
        
        for img in img_tags[:10]:  # 최대 10개 이미지
            src = img.get('src', '')
            alt = img.get('alt', '')
            title = img.get('title', '')
            
            if src:
                # 상대 경로를 절대 경로로 변환
                if src.startswith('/') and url:
                    from urllib.parse import urljoin
                    src = urljoin(url, src)
                
                images.append({
                    "src": src,
                    "alt": alt,
                    "title": title,
                    "width": img.get('width'),
                    "height": img.get('height'),
                    "confidence": 0.8 if alt or title else 0.6
                })
        
        # og:image
        og_image = soup.find('meta', property='og:image')
        if og_image and og_image.get('content'):
            images.insert(0, {
                "src": og_image['content'],
                "alt": "Open Graph Image",
                "title": "",
                "type": "og_image",
                "confidence": 0.9
            })
        
        return {
            "images": images,
            "total_images": len(images),
            "primary_image": images[0] if images else None
        }
    
    async def _extract_links(self, soup: BeautifulSoup, html: str, url: str) -> Dict:
        """링크 정보 추출"""
        links = []
        
        # 모든 a 태그 수집
        a_tags = soup.find_all('a', href=True)
        
        for a in a_tags[:20]:  # 최대 20개 링크
            href = a.get('href', '')
            text = a.get_text().strip()
            title = a.get('title', '')
            
            if href and text:
                # 상대 경로를 절대 경로로 변환
                if href.startswith('/') and url:
                    from urllib.parse import urljoin
                    href = urljoin(url, href)
                
                # 외부 링크 vs 내부 링크 구분
                is_external = href.startswith('http') and url and url not in href
                
                links.append({
                    "href": href,
                    "text": text,
                    "title": title,
                    "is_external": is_external,
                    "confidence": 0.8
                })
        
        return {
            "links": links,
            "total_links": len(links),
            "external_links": [l for l in links if l.get("is_external")],
            "internal_links": [l for l in links if not l.get("is_external")]
        }
    
    async def _extract_date(self, soup: BeautifulSoup, html: str, url: str) -> Dict:
        """날짜 정보 추출"""
        dates = []
        
        # 메타 태그에서 날짜 추출
        date_meta_selectors = [
            'meta[name="date"]',
            'meta[property="article:published_time"]',
            'meta[property="article:modified_time"]', 
            'meta[name="publish_date"]',
            'meta[name="created"]'
        ]
        
        for selector in date_meta_selectors:
            meta = soup.select_one(selector)
            if meta and meta.get('content'):
                dates.append({
                    "type": "meta_date",
                    "raw_date": meta['content'],
                    "source": selector,
                    "confidence": 0.9
                })
        
        # time 태그
        time_tags = soup.find_all('time')
        for time_tag in time_tags:
            datetime_attr = time_tag.get('datetime')
            text = time_tag.get_text().strip()
            
            if datetime_attr:
                dates.append({
                    "type": "time_tag",
                    "raw_date": datetime_attr,
                    "display_text": text,
                    "confidence": 0.8
                })
        
        # 텍스트에서 날짜 패턴 검색
        date_patterns = [
            r'\d{4}[-/.]\d{1,2}[-/.]\d{1,2}',  # YYYY-MM-DD
            r'\d{1,2}[-/.]\d{1,2}[-/.]\d{4}',  # MM-DD-YYYY
            r'\d{4}년\s*\d{1,2}월\s*\d{1,2}일',  # 한국어 날짜
            r'\d{1,2}월\s*\d{1,2}일',  # 월일만
        ]
        
        text_content = soup.get_text()
        for pattern in date_patterns:
            matches = re.findall(pattern, text_content)
            for match in matches[:3]:  # 최대 3개
                dates.append({
                    "type": "text_pattern",
                    "raw_date": match,
                    "confidence": 0.6
                })
        
        return {
            "dates": dates,
            "primary_date": dates[0] if dates else None,
            "total_found": len(dates)
        }
    
    async def _extract_from_text(self, text_content: str, target_content: str, url: str) -> Dict:
        """텍스트(마크다운)에서 추출"""
        if target_content == "제목":
            # 마크다운 헤더 추출
            headers = re.findall(r'^(#{1,3})\s+(.+)$', text_content, re.MULTILINE)
            titles = []
            
            for header_level, title_text in headers:
                titles.append({
                    "type": f"h{len(header_level)}",
                    "text": title_text.strip(),
                    "confidence": 0.9 - len(header_level) * 0.1
                })
            
            return {
                "titles": titles,
                "primary_title": titles[0]["text"] if titles else "제목을 찾을 수 없습니다",
                "total_found": len(titles)
            }
        
        elif target_content == "본문":
            # 첫 번째 헤더 이후의 내용을 본문으로 간주
            lines = text_content.split('\n')
            content_lines = []
            
            for line in lines:
                line = line.strip()
                if line and not line.startswith('#') and len(line) > 10:
                    content_lines.append(line)
            
            return {
                "paragraphs": [{"text": line, "length": len(line)} for line in content_lines[:10]],
                "full_text": '\n'.join(content_lines)[:2000],
                "total_paragraphs": len(content_lines)
            }
        
        # 기본 폴백
        return {"text": text_content[:500], "type": "fallback"}
    
    async def _extract_fallback(self, soup: BeautifulSoup, html: str, url: str) -> Dict:
        """폴백 추출 (전체 텍스트)"""
        return {
            "text": soup.get_text()[:1000] if soup else html[:1000],
            "type": "fallback_extraction",
            "message": f"'{self}' 타입은 아직 지원하지 않습니다. 전체 텍스트를 반환합니다."
        }
    
    def _calculate_extraction_quality(self, extracted_data: Dict, target_content: str) -> float:
        """추출 품질 점수 계산"""
        if not extracted_data or "error" in extracted_data:
            return 0.0
        
        base_score = 50.0
        
        if target_content == "제목":
            titles = extracted_data.get("titles", [])
            if titles:
                base_score += min(len(titles) * 10, 40)  # 제목 개수에 따라 점수
                if titles[0].get("confidence", 0) > 0.8:
                    base_score += 10
        
        elif target_content == "가격":
            prices = extracted_data.get("prices", [])
            if prices:
                base_score += min(len(prices) * 15, 45)  # 가격 개수에 따라 점수
                if prices[0] and prices[0].get("confidence", 0) > 0.7:
                    base_score += 5
        
        elif target_content == "본문":
            paragraphs = extracted_data.get("paragraphs", [])
            total_length = extracted_data.get("total_length", 0)
            if paragraphs and total_length > 100:
                base_score += min(len(paragraphs) * 5, 30)
                base_score += min(total_length / 100, 20)
        
        return min(base_score, 100.0)
    
    def _calculate_confidence(self, extracted_data: Dict) -> float:
        """신뢰도 계산"""
        if not extracted_data:
            return 0.0
        
        # 추출된 데이터의 양과 질에 따라 신뢰도 계산
        if "titles" in extracted_data:
            titles = extracted_data["titles"]
            if titles:
                return sum(t.get("confidence", 0.5) for t in titles) / len(titles)
        
        if "prices" in extracted_data:
            prices = extracted_data["prices"]
            if prices:
                return sum(p.get("confidence", 0.5) for p in prices) / len(prices)
        
        if "paragraphs" in extracted_data:
            return 0.8 if len(extracted_data["paragraphs"]) > 3 else 0.6
        
        return 0.5  # 기본 신뢰도 