import re
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

@dataclass
class SelectiveCrawlingIntent:
    """선택적 크롤링 의도"""
    urls: List[str]
    target_content: str  # "제목", "가격", "리뷰", "본문" 등
    raw_request: str
    confidence: float
    extraction_type: str  # "selective", "full"

# 🎯 통합 의도 분석 결과
@dataclass  
class UnifiedIntent:
    """통합 의도 분석 결과"""
    request_type: str    # "single", "bulk", "selective", "search"
    urls: List[str]      # 추출된 URL들
    target_content: Optional[str] = None  # 선택적 추출 타겟
    search_query: Optional[str] = None    # 검색 쿼리
    platform: Optional[str] = None       # 플랫폼 (쿠팡, 네이버 등)
    confidence: float = 0.0              # 분석 신뢰도
    raw_request: str = ""                # 원본 요청
    metadata: Dict[str, Any] = None      # 추가 메타데이터
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

class NaturalLanguageParser:
    """자연어 크롤링 요청 파서"""
    
    def __init__(self):
        # 콘텐츠 타입 매핑
        self.content_type_patterns = {
            "제목": ["제목", "타이틀", "title", "헤드라인", "headline"],
            "가격": ["가격", "price", "비용", "cost", "금액", "요금"],
            "본문": ["본문", "내용", "content", "글", "article", "텍스트", "text"],
            "리뷰": ["리뷰", "review", "후기", "평가", "댓글", "comment"],
            "요약": ["요약", "summary", "개요", "핵심", "정리"],
            "이미지": ["이미지", "image", "사진", "photo", "그림", "picture"],
            "링크": ["링크", "link", "url", "주소"],
            "날짜": ["날짜", "date", "시간", "time", "작성일"]
        }
        
        # URL 패턴
        self.url_pattern = re.compile(
            r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
        )
        
        # 간단한 도메인 패턴 (http 없이)
        self.domain_pattern = re.compile(
            r'(?:www\.)?[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*\.[a-zA-Z]{2,}'
        )
    
    def extract_urls(self, text: str) -> List[str]:
        """텍스트에서 URL 추출"""
        urls = []
        
        # 완전한 URL 추출 (http/https 포함)
        full_urls = self.url_pattern.findall(text)
        urls.extend(full_urls)
        
        # 도메인만 있는 경우 (www.test.com 형태)
        domain_matches = self.domain_pattern.findall(text)
        for domain in domain_matches:
            # 이미 full_urls에 있는지 확인
            if not any(domain in url for url in full_urls):
                # http 프로토콜 추가
                if not domain.startswith('www.'):
                    domain = 'www.' + domain
                urls.append('https://' + domain)
        
        # 중복 제거
        return list(set(urls))
    
    def detect_target_content(self, text: str) -> tuple[str, float]:
        """타겟 콘텐츠 타입 감지"""
        text_lower = text.lower()
        
        best_match = "전체"
        max_confidence = 0.0
        
        for content_type, keywords in self.content_type_patterns.items():
            confidence = 0.0
            
            for keyword in keywords:
                if keyword in text_lower:
                    # 키워드가 "만" 과 함께 사용되면 높은 신뢰도
                    if f"{keyword}만" in text_lower or f"{keyword} 만" in text_lower:
                        confidence = max(confidence, 0.8)  # 최대값으로 설정 (중복 방지)
                    # 일반적인 키워드 매칭
                    elif keyword in text_lower:
                        confidence = max(confidence, 0.5)  # 최대값으로 설정 (중복 방지)
            
            # 특정 패턴들에 대한 보너스
            if content_type == "제목" and any(word in text_lower for word in ["추출", "가져", "뽑아"]):
                confidence = min(1.0, confidence + 0.2)  # 보너스 추가하되 1.0 제한
            
            if confidence > max_confidence:
                max_confidence = confidence
                best_match = content_type
        
        # 🔧 신뢰도를 0.0~1.0 범위로 제한
        max_confidence = min(1.0, max(0.0, max_confidence))
        
        return best_match, max_confidence
    
    def parse_selective_request(self, text: str) -> SelectiveCrawlingIntent:
        """선택적 크롤링 요청 파싱"""
        logger.info(f"🔍 자연어 파싱 시작: {text}")
        
        # URL 추출
        urls = self.extract_urls(text)
        logger.info(f"📎 추출된 URL들: {urls}")
        
        # 타겟 콘텐츠 감지
        target_content, confidence = self.detect_target_content(text)
        logger.info(f"🎯 타겟 콘텐츠: {target_content} (신뢰도: {confidence:.2f})")
        
        # 추출 타입 결정
        extraction_type = "selective" if urls and target_content != "전체" else "full"
        
        intent = SelectiveCrawlingIntent(
            urls=urls,
            target_content=target_content,
            raw_request=text,
            confidence=confidence,
            extraction_type=extraction_type
        )
        
        logger.info(f"✅ 파싱 완료: {extraction_type} 크롤링, {len(urls)}개 URL")
        return intent
    
    def validate_intent(self, intent: SelectiveCrawlingIntent) -> Dict[str, Any]:
        """의도 검증 및 피드백 생성"""
        if not intent.urls:
            return {
                "is_valid": False,
                "message": "URL을 찾을 수 없습니다. 'https://example.com의 제목 추출해줘' 형식으로 입력해주세요.",
                "suggestions": [
                    "URL을 포함해주세요 (예: https://naver.com)",
                    "www.도메인.com 형식도 가능합니다",
                    "추출하고 싶은 내용을 명시해주세요 (제목, 가격, 본문 등)"
                ]
            }
        
        if not intent.target_content:
            return {
                "is_valid": False,
                "message": "추출할 콘텐츠를 지정해주세요.",
                "suggestions": [
                    "제목만 추출해줘",
                    "가격 정보 가져와줘", 
                    "본문 내용 추출해줘"
                ]
            }
        
        # 성공적인 검증
        return {
            "is_valid": True,
            "message": f"✅ {intent.urls[0]}에서 '{intent.target_content}' 추출을 시작합니다. (신뢰도: {intent.confidence:.1f})",
            "confidence": intent.confidence,
            "url": intent.urls[0],
            "target": intent.target_content
        }

    # 🎯 통합 의도 분석 메서드
    def analyze_unified_intent(self, text: str) -> UnifiedIntent:
        """
        모든 형태의 입력을 분석하여 적절한 처리 방식을 결정
        
        Args:
            text: 사용자 입력 (URL, 자연어, 멀티 URL 등)
            
        Returns:
            UnifiedIntent: 통합 의도 분석 결과
        """
        logger.info(f"🧠 통합 의도 분석 시작: {text}")
        
        # 1. URL 추출
        urls = self.extract_urls(text)
        url_count = len(urls)
        
        # 2. 자연어 패턴 분석
        has_extraction_keywords = any(keyword in text for keyword in self.content_type_patterns.keys())
        has_search_keywords = any(keyword in text for keyword in ["찾아줘", "검색", "찾기", "알아봐"])
        has_platform_keywords = any(platform in text for platform in ["쿠팡", "네이버", "구글", "아마존"])
        
        # 3. 의도 결정 로직
        if url_count == 0:
            # URL이 없는 경우
            if has_platform_keywords and has_search_keywords:
                # "쿠팡에서 콜라 찾아줘" 패턴
                return self._analyze_search_intent(text)
            else:
                # 유효하지 않은 요청
                return UnifiedIntent(
                    request_type="invalid",
                    urls=[],
                    confidence=0.0,
                    raw_request=text,
                    metadata={"error": "URL 또는 검색 의도를 찾을 수 없습니다"}
                )
        
        elif url_count == 1:
            # 단일 URL
            if has_extraction_keywords:
                # "naver.com의 제목만 추출해줘" 패턴
                return self._analyze_selective_intent(text, urls)
            else:
                # "https://example.com" 단순 URL
                return UnifiedIntent(
                    request_type="single",
                    urls=urls,
                    confidence=0.9,
                    raw_request=text,
                    metadata={"processing_type": "full_crawl"}
                )
        
        else:
            # 멀티 URL
            if has_extraction_keywords:
                # 여러 URL에서 선택적 추출 (복잡한 케이스)
                return self._analyze_bulk_selective_intent(text, urls)
            else:
                # 단순 멀티 URL 크롤링
                return UnifiedIntent(
                    request_type="bulk", 
                    urls=urls,
                    confidence=0.8,
                    raw_request=text,
                    metadata={"processing_type": "bulk_crawl", "url_count": url_count}
                )
    
    def _analyze_selective_intent(self, text: str, urls: List[str]) -> UnifiedIntent:
        """선택적 크롤링 의도 분석"""
        # 기존 selective parsing 로직 재사용
        selective_intent = self.parse_selective_request(text)
        
        return UnifiedIntent(
            request_type="selective",
            urls=urls,
            target_content=selective_intent.target_content,
            confidence=selective_intent.confidence,
            raw_request=text,
            metadata={
                "extraction_type": selective_intent.extraction_type,
                "processing_type": "selective_crawl"
            }
        )
    
    def _analyze_search_intent(self, text: str) -> UnifiedIntent:
        """검색 크롤링 의도 분석 (미래 기능)"""
        # 플랫폼 추출
        platform_patterns = {
            "쿠팡": r"쿠팡",
            "네이버": r"네이버",
            "구글": r"구글",
            "아마존": r"아마존"
        }
        
        detected_platform = None
        for platform, pattern in platform_patterns.items():
            if re.search(pattern, text, re.IGNORECASE):
                detected_platform = platform
                break
        
        # 검색 쿼리 추출 (간단한 패턴)
        search_patterns = [
            r"에서\s+(.+?)\s+찾아줘",
            r"에서\s+(.+?)\s+검색",
            r"(.+?)\s+정보\s+찾아줘"
        ]
        
        search_query = None
        for pattern in search_patterns:
            match = re.search(pattern, text)
            if match:
                search_query = match.group(1).strip()
                break
        
        return UnifiedIntent(
            request_type="search",
            urls=[],  # 검색은 URL이 없음
            search_query=search_query,
            platform=detected_platform,
            confidence=0.7 if detected_platform and search_query else 0.3,
            raw_request=text,
            metadata={
                "processing_type": "platform_search",
                "requires_implementation": True  # 아직 구현되지 않음
            }
        )
    
    def _analyze_bulk_selective_intent(self, text: str, urls: List[str]) -> UnifiedIntent:
        """멀티 URL 선택적 추출 의도 분석"""
        # 추출 타겟 분석
        target_content = None
        confidence = 0.6
        
        for keyword, content_type in self.content_type_patterns.items():
            if keyword in text:
                target_content = content_type
                confidence += 0.2
                break
        
        return UnifiedIntent(
            request_type="bulk_selective",  # 새로운 타입
            urls=urls,
            target_content=target_content,
            confidence=min(confidence, 1.0),
            raw_request=text,
            metadata={
                "processing_type": "bulk_selective_crawl",
                "url_count": len(urls),
                "requires_implementation": True  # 복잡한 케이스, 추후 구현
            }
        )

# 전역 파서 인스턴스
nl_parser = NaturalLanguageParser() 