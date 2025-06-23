"""
MCP 클라이언트 구현
백엔드에서 MCP 도구와 직접 통신하기 위한 클라이언트
"""

import asyncio
import logging
import json
import os
import sys
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)

# MCP 서버 도구들 직접 임포트
try:
    # mcp-server 디렉토리를 Python 경로에 추가
    current_dir = os.path.dirname(os.path.abspath(__file__))
    backend_dir = os.path.dirname(os.path.dirname(current_dir))  # ai-crawler/backend
    project_root = os.path.dirname(backend_dir)  # ai-crawler
    mcp_server_dir = os.path.join(project_root, "mcp-server")
    
    if mcp_server_dir not in sys.path:
        sys.path.insert(0, mcp_server_dir)
    
    from tools.site_analyzer import SiteAnalyzer
    from tools.crawler_selector import CrawlerSelector  
    from tools.structure_detector import StructureDetector
    from tools.quality_validator import QualityValidator
    
    logger.info("🔧 MCP 도구들 직접 임포트 성공")
    
except ImportError as e:
    logger.error(f"❌ MCP 도구 임포트 실패: {e}")
    raise

class MCPClient:
    """MCP 도구와 직접 통신하는 클라이언트"""
    
    def __init__(self):
        """MCP 클라이언트 초기화 - 도구 인스턴스 생성"""
        try:
            self.site_analyzer = SiteAnalyzer()
            self.crawler_selector = CrawlerSelector()
            self.structure_detector = StructureDetector()
            self.quality_validator = QualityValidator()
            
            logger.info("✅ MCP 도구 인스턴스 생성 완료")
        except Exception as e:
            logger.error(f"❌ MCP 도구 초기화 실패: {e}")
            raise
        
    def connect(self):
        """연결 컨텍스트 매니저 (호환성을 위한 더미)"""
        class DummyAsyncContext:
            def __init__(self, client):
                self.client = client
            
            async def __aenter__(self):
                return self.client
            
            async def __aexit__(self, exc_type, exc_val, exc_tb):
                pass
        
        return DummyAsyncContext(self)
    
    async def analyze_site(self, url: str, sample_html: str = "", headers: Dict[str, Any] = None) -> Dict[str, Any]:
        """사이트 분석 및 크롤러 선택"""
        if headers is None:
            headers = {}
            
        try:
            logger.info(f"🔍 사이트 분석 시작: {url}")
            result = await self.site_analyzer.analyze_and_select(
                url=url,
                sample_html=sample_html,
                headers=headers
            )
            logger.info("✅ 사이트 분석 완료")
            return result
        except Exception as e:
            logger.error(f"❌ 사이트 분석 실패: {e}")
            return {
                "error": str(e),
                "url": url,
                "status": "failed"
            }
    
    async def detect_structure(self, html_sample: str, url: str = "") -> Dict[str, Any]:
        """콘텐츠 구조 분석"""
        try:
            logger.info(f"🔍 구조 분석 시작: {url}")
            result = await self.structure_detector.detect_structure(
                html_sample=html_sample,
                url=url
            )
            logger.info("✅ 구조 분석 완료")
            return result
        except Exception as e:
            logger.error(f"❌ 구조 분석 실패: {e}")
            return {
                "error": str(e),
                "url": url,
                "status": "failed"
            }
    
    async def generate_strategy(self, site_analysis: Dict[str, Any], content_structure: Dict[str, Any]) -> Dict[str, Any]:
        """크롤링 전략 생성"""
        try:
            logger.info("🔍 전략 생성 시작")
            result = await self.crawler_selector.generate_strategy(
                site_analysis=site_analysis,
                content_structure=content_structure
            )
            logger.info("✅ 전략 생성 완료")
            return result
        except Exception as e:
            logger.error(f"❌ 전략 생성 실패: {e}")
            return {
                "error": str(e),
                "status": "failed"
            }
    
    async def validate_result(self, extracted_data: Dict[str, Any], url: str, expected_quality: float = 70.0) -> Dict[str, Any]:
        """크롤링 결과 검증"""
        try:
            logger.info(f"🔍 품질 검증 시작: {url}")
            result = await self.quality_validator.validate_result(
                extracted_data=extracted_data,
                url=url,
                expected_quality=expected_quality
            )
            logger.info("✅ 품질 검증 완료")
            return result
        except Exception as e:
            logger.error(f"❌ 품질 검증 실패: {e}")
            return {
                "error": str(e),
                "url": url,
                "status": "failed"
            }
    
    async def extract_selective_content(self, html_content: str, target_content: str, url: str = "") -> Dict[str, Any]:
        """선택적 콘텐츠 추출"""
        try:
            logger.info(f"🎯 선택적 추출 시작: {target_content} from {url}")
            
            # content_extractor가 없는 경우 임포트 시도
            if not hasattr(self, 'content_extractor'):
                from tools.content_extractor import ContentExtractor
                self.content_extractor = ContentExtractor()
            
            result = await self.content_extractor.extract_selective_content(
                html_content=html_content,
                target_content=target_content,
                url=url
            )
            logger.info("✅ 선택적 추출 완료")
            return result
        except Exception as e:
            logger.error(f"❌ 선택적 추출 실패: {e}")
            return {
                "error": str(e),
                "target_content": target_content,
                "url": url,
                "status": "failed"
            } 