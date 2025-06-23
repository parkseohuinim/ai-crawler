"""
사용자 친화적인 에러 메시지 포맷터
보안상 민감한 정보(파일 경로, 코드 라인 등)를 제거하고 사용자가 이해하기 쉬운 메시지로 변환
"""

import re
from typing import Dict, List, Optional
from datetime import datetime

class ErrorFormatter:
    """에러 메시지를 사용자 친화적으로 변환하는 클래스"""
    
    # 에러 패턴과 사용자 친화적인 메시지 매핑
    ERROR_PATTERNS = {
        # 타임아웃 관련
        r"timeout.*exceeded|timed out|connection timeout": {
            "message": "웹사이트 응답 시간이 초과되었습니다",
            "suggestion": "잠시 후 다시 시도해보세요"
        },
        
        # 네트워크 연결 관련
        r"connection.*refused|connection.*failed|network.*unreachable": {
            "message": "웹사이트에 연결할 수 없습니다",
            "suggestion": "인터넷 연결을 확인하거나 잠시 후 다시 시도해보세요"
        },
        
        # DNS 관련
        r"name.*resolution.*failed|dns.*error|host.*not.*found": {
            "message": "웹사이트 주소를 찾을 수 없습니다",
            "suggestion": "URL이 올바른지 확인해보세요"
        },
        
        # HTTP 에러
        r"404|not found": {
            "message": "요청한 페이지를 찾을 수 없습니다",
            "suggestion": "URL이 올바른지 확인해보세요"
        },
        
        r"403|forbidden|access.*denied": {
            "message": "페이지 접근이 거부되었습니다",
            "suggestion": "해당 웹사이트에서 크롤링을 허용하지 않을 수 있습니다"
        },
        
        r"500|internal.*server.*error": {
            "message": "웹사이트 서버에 오류가 발생했습니다",
            "suggestion": "잠시 후 다시 시도해보세요"
        },
        
        r"502|bad.*gateway": {
            "message": "웹사이트 서버가 일시적으로 사용할 수 없습니다",
            "suggestion": "잠시 후 다시 시도해보세요"
        },
        
        r"503|service.*unavailable": {
            "message": "웹사이트 서비스가 일시적으로 중단되었습니다",
            "suggestion": "잠시 후 다시 시도해보세요"
        },
        
        # SSL/TLS 관련
        r"ssl.*certificate|certificate.*verify.*failed|ssl.*error": {
            "message": "웹사이트의 보안 인증서에 문제가 있습니다",
            "suggestion": "해당 웹사이트의 보안 설정을 확인해보세요"
        },
        
        # 봇 차단 관련
        r"bot.*detected|captcha|cloudflare|access.*denied.*bot": {
            "message": "웹사이트에서 자동화된 접근을 차단했습니다",
            "suggestion": "해당 웹사이트는 크롤링을 허용하지 않을 수 있습니다"
        },
        
        # 페이지 로딩 관련
        r"page.*goto.*failed|navigation.*failed|load.*failed": {
            "message": "페이지를 불러올 수 없습니다",
            "suggestion": "웹사이트가 일시적으로 접근하기 어려울 수 있습니다"
        },
        
        # JavaScript 관련
        r"javascript.*error|script.*error": {
            "message": "페이지의 동적 콘텐츠를 처리하는 중 오류가 발생했습니다",
            "suggestion": "해당 페이지는 복잡한 구조를 가지고 있을 수 있습니다"
        },
        
        # 메모리 관련
        r"memory.*error|out.*of.*memory": {
            "message": "페이지가 너무 복잡하여 처리할 수 없습니다",
            "suggestion": "더 간단한 페이지로 시도해보세요"
        },
        
        # 일반적인 크롤링 실패
        r"crawling.*failed|scraping.*failed": {
            "message": "페이지 내용을 추출할 수 없습니다",
            "suggestion": "다른 크롤링 방식을 시도하거나 잠시 후 다시 시도해보세요"
        }
    }
    
    # 엔진별 설명
    ENGINE_DESCRIPTIONS = {
        "requests": "기본 HTTP 크롤러",
        "firecrawl": "고급 크롤링 서비스",
        "crawl4ai": "AI 기반 크롤러",
        "playwright": "브라우저 자동화"
    }
    
    @classmethod
    def format_error_message(cls, error: str, url: str = "", attempted_engines: List[str] = None) -> Dict[str, str]:
        """
        에러 메시지를 사용자 친화적으로 포맷팅
        
        Args:
            error: 원본 에러 메시지
            url: 실패한 URL
            attempted_engines: 시도한 엔진 목록
            
        Returns:
            Dict containing formatted error information
        """
        if not error:
            error = "알 수 없는 오류가 발생했습니다"
        
        # 민감한 정보 제거
        clean_error = cls._sanitize_error_message(error)
        
        # 패턴 매칭으로 사용자 친화적인 메시지 생성
        user_message = cls._match_error_pattern(clean_error)
        
        # 엔진 정보 포맷팅
        engine_info = cls._format_engine_info(attempted_engines)
        
        return {
            "user_message": user_message["message"],
            "suggestion": user_message["suggestion"],
            "technical_summary": cls._create_technical_summary(clean_error, attempted_engines),
            "engine_info": engine_info,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
    
    @classmethod
    def _sanitize_error_message(cls, error: str) -> str:
        """민감한 정보를 제거하고 에러 메시지를 정리"""
        if not error:
            return "알 수 없는 오류"
        
        # 파일 경로 제거 (절대 경로)
        error = re.sub(r'/[^/\s]+/[^/\s]+/[^/\s]+/[^\s]+\.py', '[파일]', error)
        error = re.sub(r'C:\\[^\\s]+\\[^\\s]+\\[^\s]+\.py', '[파일]', error)
        
        # 라인 번호 제거
        error = re.sub(r'at line \d+', '', error)
        error = re.sub(r'line \d+:', '', error)
        
        # 코드 컨텍스트 제거
        error = re.sub(r'Code context:.*?(?=\n\n|\Z)', '', error, flags=re.DOTALL)
        
        # 스택 트레이스 제거
        error = re.sub(r'Traceback \(most recent call last\):.*?(?=\n\n|\Z)', '', error, flags=re.DOTALL)
        
        # 긴 파일 경로나 시스템 경로 제거
        error = re.sub(r'[/\\][a-zA-Z0-9_\-./\\]+?\.py', '[파일]', error)
        
        # 여러 줄바꿈을 하나로 정리
        error = re.sub(r'\n\s*\n', '\n', error)
        
        # 앞뒤 공백 제거
        error = error.strip()
        
        return error
    
    @classmethod
    def _match_error_pattern(cls, error: str) -> Dict[str, str]:
        """에러 패턴을 매칭하여 사용자 친화적인 메시지 반환"""
        error_lower = error.lower()
        
        for pattern, message_info in cls.ERROR_PATTERNS.items():
            if re.search(pattern, error_lower):
                return message_info
        
        # 매칭되는 패턴이 없는 경우 기본 메시지
        return {
            "message": "페이지를 처리하는 중 오류가 발생했습니다",
            "suggestion": "다른 URL로 시도하거나 잠시 후 다시 시도해보세요"
        }
    
    @classmethod
    def _format_engine_info(cls, attempted_engines: List[str] = None) -> str:
        """시도한 엔진 정보를 사용자 친화적으로 포맷팅"""
        if not attempted_engines:
            return "크롤링 엔진 정보 없음"
        
        engine_descriptions = []
        for engine in attempted_engines:
            desc = cls.ENGINE_DESCRIPTIONS.get(engine, engine)
            engine_descriptions.append(f"{engine}({desc})")
        
        return f"시도한 방법: {', '.join(engine_descriptions)}"
    
    @classmethod
    def _create_technical_summary(cls, error: str, attempted_engines: List[str] = None) -> str:
        """기술적 요약 생성 (개발자용)"""
        summary_parts = []
        
        if attempted_engines:
            summary_parts.append(f"시도한 엔진: {len(attempted_engines)}개")
        
        # 에러 타입 추출
        if "timeout" in error.lower():
            summary_parts.append("타입: 타임아웃")
        elif "connection" in error.lower():
            summary_parts.append("타입: 연결 오류")
        elif "404" in error or "not found" in error.lower():
            summary_parts.append("타입: 페이지 없음")
        elif "403" in error or "forbidden" in error.lower():
            summary_parts.append("타입: 접근 거부")
        else:
            summary_parts.append("타입: 일반 오류")
        
        return " | ".join(summary_parts) if summary_parts else "요약 정보 없음"

# 편의 함수들
def format_crawling_error(error: str, url: str = "", attempted_engines: List[str] = None) -> str:
    """크롤링 에러를 사용자 친화적인 메시지로 변환"""
    formatted = ErrorFormatter.format_error_message(error, url, attempted_engines)
    
    message_parts = [formatted["user_message"]]
    
    if formatted["suggestion"]:
        message_parts.append(f"💡 {formatted['suggestion']}")
    
    if formatted["engine_info"] and attempted_engines:
        message_parts.append(f"🔧 {formatted['engine_info']}")
    
    return " | ".join(message_parts)

def get_simple_error_message(error: str) -> str:
    """가장 간단한 에러 메시지만 반환"""
    formatted = ErrorFormatter.format_error_message(error)
    return formatted["user_message"] 