#!/usr/bin/env python3
"""
MCP 서버 메인 모듈 (OpenAI MCP 표준)
PROJECT_SPECIFICATION.md 요구사항에 따른 올바른 MCP 구현
"""

import os
import sys
import json
import asyncio
import logging
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv

# MCP 라이브러리 임포트
from mcp.server.fastmcp import FastMCP

# 현재 디렉토리를 Python 경로에 추가
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

from tools.site_analyzer import SiteAnalyzer
from tools.crawler_selector import CrawlerSelector  
from tools.structure_detector import StructureDetector
from tools.quality_validator import QualityValidator
from tools.content_extractor import ContentExtractor

# 환경 변수 로드 (루트 디렉토리에서)
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# MCP 서버 초기화 (OpenAI MCP 표준)
mcp = FastMCP("AI Crawler MCP Server")

# MCP 도구 인스턴스들
site_analyzer = SiteAnalyzer()
crawler_selector = CrawlerSelector()
structure_detector = StructureDetector()
quality_validator = QualityValidator()
content_extractor = ContentExtractor()

print(f"🧠 MCP 서버 시작: {mcp.name}")

@mcp.tool()
async def analyze_site_and_select_crawler(url: str, sample_html: str = "", headers: dict = {}) -> dict:
    """
    사이트 종합 분석 및 최적 크롤러 선택:
    - SPA/SSR/Static 판별
    - JavaScript 복잡도 분석
    - 안티봇 시스템 감지
    - 콘텐츠 로딩 방식 파악
    - 추천 크롤링 엔진 결정
    
    Args:
        url: 분석할 웹사이트 URL
        sample_html: 사이트 샘플 HTML (선택사항)
        headers: HTTP 헤더 정보 (선택사항)
    
    Returns:
        사이트 분석 결과 및 추천 크롤러 정보
    """
    try:
        logger.info(f"사이트 분석 시작: {url}")
        result = await site_analyzer.analyze_and_select(
            url=url,
            sample_html=sample_html,
            headers=headers
        )
        return result
    except Exception as e:
        logger.error(f"사이트 분석 오류: {e}")
        return {
            "error": str(e),
            "url": url,
            "status": "failed"
        }

@mcp.tool()
async def detect_content_structure(html_sample: str, url: str = "") -> dict:
    """
    콘텐츠 구조 패턴 분석:
    - 계층구조 식별
    - 주요 콘텐츠 영역 감지
    - 네비게이션/사이드바 구분
    - 제목/본문 패턴 인식
    
    Args:
        html_sample: 분석할 HTML 샘플
        url: 원본 URL (선택사항)
    
    Returns:
        콘텐츠 구조 분석 결과
    """
    try:
        logger.info(f"콘텐츠 구조 분석 시작 (URL: {url})")
        result = await structure_detector.detect_structure(
            html_sample=html_sample,
            url=url
        )
        return result
    except Exception as e:
        logger.error(f"구조 분석 오류: {e}")
        return {
            "error": str(e),
            "url": url,
            "status": "failed"
        }

@mcp.tool()
async def generate_extraction_strategy(site_analysis: dict, content_structure: dict) -> dict:
    """
    추출 전략 수립:
    - 엔진별 최적 설정
    - CSS 셀렉터 규칙
    - 제외 영역 정의
    - 후처리 방법
    
    Args:
        site_analysis: 사이트 분석 결과
        content_structure: 콘텐츠 구조 분석 결과
    
    Returns:
        크롤링 전략 및 설정
    """
    try:
        logger.info("추출 전략 생성 시작")
        result = await crawler_selector.generate_strategy(
            site_analysis=site_analysis,
            content_structure=content_structure
        )
        return result
    except Exception as e:
        logger.error(f"전략 생성 오류: {e}")
        return {
            "error": str(e),
            "status": "failed"
        }

@mcp.tool()
async def validate_crawling_result(extracted_data: dict, url: str, expected_quality: float = 70.0) -> dict:
    """
    크롤링 결과 품질 검증:
    - 필수 콘텐츠 존재 확인
    - 텍스트 품질 평가
    - 구조적 완성도 검사
    - 재시도 필요성 판단
    
    Args:
        extracted_data: 추출된 데이터
        url: 원본 URL
        expected_quality: 기대 품질 점수 (기본값: 70.0)
    
    Returns:
        품질 검증 결과
    """
    try:
        logger.info(f"품질 검증 시작: {url}")
        result = await quality_validator.validate_result(
            extracted_data=extracted_data,
            url=url,
            expected_quality=expected_quality
        )
        return result
    except Exception as e:
        logger.error(f"품질 검증 오류: {e}")
        return {
            "error": str(e),
            "url": url,
            "status": "failed"
        }

@mcp.tool()
async def extract_selective_content(html_content: str, target_content: str, url: str = "") -> dict:
    """
    선택적 콘텐츠 추출:
    - 제목만 추출
    - 가격만 추출  
    - 본문만 추출
    - 리뷰만 추출
    - 기타 특정 부분만 추출
    
    Args:
        html_content: HTML 내용 또는 마크다운 텍스트
        target_content: 추출할 콘텐츠 타입 ("제목", "가격", "본문", "리뷰" 등)
        url: 원본 URL (선택사항)
    
    Returns:
        선택적으로 추출된 콘텐츠 데이터
    """
    try:
        logger.info(f"선택적 콘텐츠 추출 시작: {target_content} from {url}")
        result = await content_extractor.extract_selective_content(
            html_content=html_content,
            target_content=target_content,
            url=url
        )
        return result
    except Exception as e:
        logger.error(f"선택적 추출 오류: {e}")
        return {
            "error": str(e),
            "target_content": target_content,
            "url": url,
            "status": "failed"
        }

if __name__ == "__main__":
    # MCP 서버 실행 (stdio 전송 방식)
    mcp.run(transport="stdio") 