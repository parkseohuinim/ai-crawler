import re
from typing import Dict, Any, Optional
from ..crawlers.base import CrawlResult
from datetime import datetime

def clean_crawled_text(text: str) -> str:
    """
    크롤링된 텍스트에서 불필요한 요소들을 제거하고 가독성을 개선합니다.
    
    Args:
        text: 원본 크롤링된 텍스트
        
    Returns:
        정제된 텍스트
    """
    if not text or not isinstance(text, str):
        return ""
    
    # 1. 이스케이프 문자 정리 (더 강력하게)
    cleaned = text.replace('\\n', '\n').replace('\\t', '\t').replace('\\"', '"').replace("\\'", "'")
    cleaned = re.sub(r'\\([()])', r'\1', cleaned)  # \( \) 같은 백슬래시 이스케이핑 제거
    
    # 2. JavaScript 링크 및 불필요한 링크 제거
    # [텍스트](javascript:...) 형태의 링크를 텍스트만 남기도록 변경 (중첩 괄호 처리)
    cleaned = re.sub(r'\[([^\]]+)\]\(javascript:[^)]*(?:\([^)]*\))*[^)]*\)', r'\1', cleaned)
    # [텍스트](#...) 형태의 앵커 링크도 텍스트만 남김
    cleaned = re.sub(r'\[([^\]]+)\]\(#[^)]*\)', r'\1', cleaned)
    # mailto: 링크도 제거
    cleaned = re.sub(r'\[([^\]]+)\]\(mailto:[^)]*\)', r'\1', cleaned)
    # HTTP/HTTPS 링크는 유지하되, 긴 링크는 도메인만 표시
    cleaned = re.sub(r'\[([^\]]+)\]\((https?://[^/)]+)/[^)]*\)', r'\1 (\2)', cleaned)
    
    # 3. UI 요소 제거 (더 포괄적으로)
    ui_patterns = [
        r'_[^_]*아이콘_',  # _아이콘_ 패턴
        r'_[^_]*버튼_',   # _버튼_ 패턴
        r'_[^_]*링크_',   # _링크_ 패턴
        r'로그인전\s*아이콘\s*',
        r'\s*바로가기\s*$',  # 바로가기 (앞뒤 공백 포함)
        r'\s*더보기\s*$',    # 더보기 (앞뒤 공백 포함)
        r'검색\s*$',        # 줄 끝의 '검색'
        r'로그인\s*$',      # 줄 끝의 '로그인'
        r'본문\s*바로가기.*?바로\s*가기',  # 접근성 링크들
        r'\s*새창열림\s*',  # "새창열림" 텍스트
        r'\s*펼치기\s*',    # "펼치기" 텍스트
        r'"[^"]*새창열림[^"]*"',  # 새창열림 관련 텍스트
        r'"[^"]*펼치기[^"]*"',   # 펼치기 관련 텍스트
    ]
    
    for pattern in ui_patterns:
        cleaned = re.sub(pattern, '', cleaned, flags=re.MULTILINE | re.IGNORECASE)
    
    # 3. 마크다운 및 구분선 정리 (더 철저하게)
    # 연속된 헤더 마크다운 정리
    cleaned = re.sub(r'#{4,}', '###', cleaned)
    
    # 불필요한 구분선 제거 (다양한 패턴)
    cleaned = re.sub(r'^[\*\-_]{3,}\s*$', '', cleaned, flags=re.MULTILINE)
    cleaned = re.sub(r'^\*\s*\*\s*\*\s*$', '', cleaned, flags=re.MULTILINE)
    
    # 4. 리스트 형식 통일 (* 를 - 로 변경하여 일관성 확보)
    cleaned = re.sub(r'^(\s*)\*\s+', r'\1- ', cleaned, flags=re.MULTILINE)
    
    # 5. 불필요한 공백과 개행 정리
    # 연속된 공백을 하나로
    cleaned = re.sub(r' {2,}', ' ', cleaned)
    
    # 줄 끝 공백 제거
    cleaned = re.sub(r' +$', '', cleaned, flags=re.MULTILINE)
    
    # 연속된 개행을 최대 2개로 제한
    cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
    
    # 6. 문장 구조 개선
    lines = cleaned.split('\n')
    improved_lines = []
    
    for line in lines:
        line = line.strip()
        if not line:
            improved_lines.append('')
            continue
            
        # 의미없는 단독 문자 제거
        if len(line) == 1 and line in '#*-_':
            continue
            
        # 너무 짧은 리스트 아이템 제거
        if line.startswith('* ') and len(line) < 5:
            continue
            
        # 해시태그 패턴 정리 (# 인터넷 접속불가# TV 리모컨 -> # 인터넷 접속불가 # TV 리모컨)
        if '#' in line and not line.startswith('#'):
            line = re.sub(r'#\s*([^#]+?)#', r'# \1 #', line)
            line = re.sub(r'#\s*([^#]+?)$', r'# \1', line)
        
        improved_lines.append(line)
    
    # 7. 최종 정리
    result = '\n'.join(improved_lines)
    
    # 시작과 끝의 공백 제거
    result = result.strip()
    
    # 연속된 빈 줄 최종 정리
    result = re.sub(r'\n{3,}', '\n\n', result)
    
    return result

def extract_main_content(text: str) -> str:
    """
    텍스트에서 주요 컨텐츠만 추출합니다.
    네비게이션, 푸터, 사이드바 등을 제거하고 본문 내용만 남깁니다.
    
    Args:
        text: 원본 텍스트
        
    Returns:
        주요 컨텐츠만 추출된 텍스트
    """
    if not text:
        return ""
    
    # 🔧 실제 입력 텍스트를 처리하도록 수정
    cleaned = text
    
    # 1. 대규모 불필요 섹션 제거
    # 전체 네비게이션 메뉴 블록들을 통째로 제거
    major_navigation_blocks = [
        r'\*\*QUICK MENU\*\*.*?(?=##|\n\n\*\*|$)',  # 퀵메뉴 전체 블록
        r'\*\*인기메뉴\*\*.*?(?=##|\*\*kt|\n\n|$)',  # 인기메뉴 블록
        r'\*\*!\[kt.*?(?=##|^\*\s|$)',  # KT 네비게이션 메뉴 전체
        r'^\*\s+Shop.*?(?=##|^\*[^*]|$)',  # Shop 메뉴 전체 섹션
        r'^\*\s+상품.*?(?=##|^\*[^*]|$)',  # 상품 메뉴 전체 섹션  
        r'^\*\s+로밍.*?(?=##|^\*[^*]|$)',  # 로밍 메뉴 전체 섹션
        r'Family Site.*?$',  # Family Site 섹션
        r'\[그룹사 소개\].*?$',  # 그룹사 소개
        r'\(주\)케이티.*?맨위로 스크롤',  # 푸터 전체
    ]
    
    for pattern in major_navigation_blocks:
        cleaned = re.sub(pattern, '', cleaned, flags=re.DOTALL | re.MULTILINE | re.IGNORECASE)
    
    # 2. 세부 불필요 요소 제거
    detailed_patterns = [
        r'본문 바로가기.*?바로 가기',  # 접근성 링크들
        r'평일오전.*?오후\d+시',  # 운영시간 정보들
        r'\d{4}-\d{4}\s*\(.*?\)',  # 전화번호 패턴
        r'Copyright.*?ALL RIGHTS RESERVED\.?',  # 저작권 정보
        r'COPYRIGHTⓒ.*?ALL RIGHTS RESERVED\.?',
        r';?\)$',  # 줄 끝의 ;) 패턴
        r'https?://[^\s)]+\)',  # URL이 포함된 괄호 패턴
        r'\([^)]*https?://[^)]*\)',  # 괄호 안의 URL들
    ]
    
    for pattern in detailed_patterns:
        cleaned = re.sub(pattern, '', cleaned, flags=re.MULTILINE | re.IGNORECASE)
    
    # 3. 기본 텍스트 정리 적용
    return clean_crawled_text(cleaned)

def get_processing_quality_score(original_text: str, cleaned_text: str) -> float:
    """
    텍스트 후처리 품질 점수를 계산합니다.
    
    Args:
        original_text: 원본 텍스트
        cleaned_text: 정제된 텍스트
        
    Returns:
        품질 점수 (0.0 ~ 1.0)
    """
    if not original_text or not cleaned_text:
        return 0.0
    
    # 정제 후 텍스트 길이 비율
    length_ratio = len(cleaned_text) / len(original_text)
    
    # 마크다운 문법 감소 정도
    markdown_before = len(re.findall(r'[#\*\-]{2,}', original_text))
    markdown_after = len(re.findall(r'[#\*\-]{2,}', cleaned_text))
    markdown_reduction = (markdown_before - markdown_after) / max(markdown_before, 1)
    
    # UI 요소 제거 정도
    ui_before = len(re.findall(r'_[^_]*_|아이콘|버튼', original_text))
    ui_after = len(re.findall(r'_[^_]*_|아이콘|버튼', cleaned_text))
    ui_reduction = (ui_before - ui_after) / max(ui_before, 1)
    
    # 종합 품질 점수 (가중 평균)
    quality_score = (
        length_ratio * 0.4 +        # 내용 보존도
        markdown_reduction * 0.3 +   # 마크다운 정리도
        ui_reduction * 0.3          # UI 요소 제거도
    )
    
    return min(max(quality_score, 0.0), 1.0)

def post_process_crawl_result(crawl_result: CrawlResult, clean_text: bool = True) -> CrawlResult:
    """
    크롤링 결과에 후처리를 적용합니다.
    
    Args:
        crawl_result: 원본 크롤링 결과
        clean_text: 텍스트 정제 적용 여부
        
    Returns:
        후처리가 적용된 크롤링 결과
    """
    if not clean_text or not crawl_result.text:
        return crawl_result
    
    # 원본 텍스트 보존
    original_text = crawl_result.text
    
    # 텍스트 정제
    cleaned_text = extract_main_content(original_text)
    processing_quality = get_processing_quality_score(original_text, cleaned_text)
    
    # 새로운 메타데이터 생성 (기존 메타데이터 보존)
    new_metadata = crawl_result.metadata.copy()
    new_metadata.update({
        "post_processing_applied": True,
        "original_text_length": len(original_text),
        "processed_text_length": len(cleaned_text),
        "text_reduction_ratio": len(cleaned_text) / len(original_text) if original_text else 1.0,
        "processing_quality_score": processing_quality,
        "processing_timestamp": datetime.now().isoformat()
    })
    
    # 후처리된 결과 반환
    return CrawlResult(
        url=crawl_result.url,
        title=crawl_result.title,
        text=cleaned_text,
        hierarchy=crawl_result.hierarchy,
        metadata=new_metadata,
        status=crawl_result.status,
        timestamp=crawl_result.timestamp,
        error=crawl_result.error
    )

def create_processing_options() -> Dict[str, Any]:
    """
    사용 가능한 후처리 옵션들을 반환합니다.
    """
    return {
        "clean_text": {
            "description": "불필요한 UI 요소, 과도한 마크다운 제거",
            "default": True
        },
        "extract_main_content": {
            "description": "주요 컨텐츠만 추출 (네비게이션, 푸터 제거)",
            "default": True
        },
        "preserve_original": {
            "description": "원본 텍스트 메타데이터에 보존",
            "default": True
        }
    } 