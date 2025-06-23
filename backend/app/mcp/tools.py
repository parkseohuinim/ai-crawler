"""
MCP 도구 관리자
MCP 클라이언트를 통해 다양한 분석 도구들을 편리하게 사용할 수 있는 인터페이스
"""

import logging
from typing import Dict, Any, Optional
from .client import MCPClient

logger = logging.getLogger(__name__)

class MCPToolsManager:
    """MCP 도구들을 관리하는 매니저 클래스"""
    
    def __init__(self, mcp_client: MCPClient):
        """
        MCP 도구 매니저 초기화
        
        Args:
            mcp_client: MCP 클라이언트 인스턴스
        """
        self.mcp_client = mcp_client
        self._available_tools = None
    
    async def get_available_tools(self) -> Dict[str, Any]:
        """사용 가능한 도구 목록 조회"""
        if self._available_tools is None:
            tools_list = await self.mcp_client.list_tools()
            self._available_tools = {tool["name"]: tool for tool in tools_list}
            logger.info(f"사용 가능한 MCP 도구: {list(self._available_tools.keys())}")
        
        return self._available_tools
    
    async def analyze_website_completely(self, url: str, sample_html: str = "") -> Dict[str, Any]:
        """
        웹사이트 종합 분석 워크플로우
        사이트 분석 → 구조 감지 → 전략 생성의 전체 과정 실행
        
        Args:
            url: 분석할 웹사이트 URL
            sample_html: 선택적 HTML 샘플
            
        Returns:
            전체 분석 결과
        """
        logger.info(f"웹사이트 종합 분석 시작: {url}")
        
        # 🔧 디버깅: 입력 매개변수 확인
        logger.info(f"🔧 DEBUG: 분석 매개변수:")
        logger.info(f"   - URL: {url}")
        logger.info(f"   - Sample HTML 길이: {len(sample_html)}")
        logger.info(f"   - MCP 클라이언트 상태: {self.mcp_client is not None}")
        
        try:
            # 1단계: 사이트 분석 및 크롤러 선택
            logger.info("1단계: 사이트 분석 중...")
            logger.info(f"🔧 DEBUG: mcp_client.analyze_site 호출 시작")
            
            site_analysis = await self.mcp_client.analyze_site(url, sample_html)
            
            logger.info(f"🔧 DEBUG: mcp_client.analyze_site 완료")
            logger.info(f"🔧 DEBUG: site_analysis 타입: {type(site_analysis)}")
            logger.info(f"🔧 DEBUG: site_analysis 키들: {list(site_analysis.keys()) if isinstance(site_analysis, dict) else 'Not a dict'}")
            
            if "error" in site_analysis:
                logger.error(f"🔧 DEBUG: 사이트 분석에서 에러 감지: {site_analysis['error']}")
                logger.error(f"사이트 분석 실패: {site_analysis['error']}")
                return {"error": "사이트 분석 실패", "details": site_analysis}
            
            logger.info(f"🔧 DEBUG: 사이트 분석 성공!")
            if "recommended_crawler" in site_analysis:
                logger.info(f"🔧 DEBUG: 추천 크롤러: {site_analysis['recommended_crawler']}")
            
            # 2단계: 콘텐츠 구조 분석
            logger.info("2단계: 콘텐츠 구조 분석 중...")
            logger.info(f"🔧 DEBUG: mcp_client.detect_structure 호출 시작")
            
            if sample_html:
                structure_analysis = await self.mcp_client.detect_structure(sample_html, url)
            else:
                # HTML 샘플이 없으면 기본 구조로 진행
                logger.info(f"🔧 DEBUG: HTML 샘플이 없어서 기본 구조 사용")
                structure_analysis = await self.mcp_client.detect_structure(
                    "<html><body><p>기본 구조</p></body></html>", url
                )
            
            logger.info(f"🔧 DEBUG: mcp_client.detect_structure 완료")
            logger.info(f"🔧 DEBUG: structure_analysis 타입: {type(structure_analysis)}")
            logger.info(f"🔧 DEBUG: structure_analysis 키들: {list(structure_analysis.keys()) if isinstance(structure_analysis, dict) else 'Not a dict'}")
            
            if "error" in structure_analysis:
                logger.warning(f"🔧 DEBUG: 구조 분석에서 에러 감지: {structure_analysis['error']}")
                logger.warning(f"구조 분석 실패, 기본 구조 사용: {structure_analysis['error']}")
                structure_analysis = {"basic_structure": True}
            
            # 3단계: 크롤링 전략 생성
            logger.info("3단계: 크롤링 전략 생성 중...")
            logger.info(f"🔧 DEBUG: mcp_client.generate_strategy 호출 시작")
            
            strategy = await self.mcp_client.generate_strategy(site_analysis, structure_analysis)
            
            logger.info(f"🔧 DEBUG: mcp_client.generate_strategy 완료")
            logger.info(f"🔧 DEBUG: strategy 타입: {type(strategy)}")
            logger.info(f"🔧 DEBUG: strategy 키들: {list(strategy.keys()) if isinstance(strategy, dict) else 'Not a dict'}")
            
            if "error" in strategy:
                logger.error(f"🔧 DEBUG: 전략 생성에서 에러 감지: {strategy['error']}")
                logger.error(f"전략 생성 실패: {strategy['error']}")
                return {"error": "전략 생성 실패", "details": strategy}
            
            logger.info(f"🔧 DEBUG: 전략 생성 성공!")
            if "recommended_engine" in strategy:
                logger.info(f"🔧 DEBUG: 전략에서 추천 엔진: {strategy['recommended_engine']}")
            if "fallback_engines" in strategy:
                logger.info(f"🔧 DEBUG: 전략에서 폴백 엔진들: {strategy['fallback_engines']}")
            
            # 결과 종합
            complete_analysis = {
                "url": url,
                "site_analysis": site_analysis,
                "structure_analysis": structure_analysis,
                "crawling_strategy": strategy,
                "status": "success",
                "workflow_completed": True
            }
            
            # 🔧 디버깅: 최종 결과 확인
            logger.info(f"🔧 DEBUG: 최종 결과 구성 완료")
            logger.info(f"🔧 DEBUG: complete_analysis 키들: {list(complete_analysis.keys())}")
            
            logger.info(f"웹사이트 종합 분석 완료: {url}")
            return complete_analysis
            
        except Exception as e:
            # 🔧 디버깅: 예외 상세 정보
            logger.error(f"🔧 DEBUG: analyze_website_completely에서 예외 발생!")
            logger.error(f"🔧 DEBUG: 예외 타입: {type(e).__name__}")
            logger.error(f"🔧 DEBUG: 예외 메시지: {str(e)}")
            logger.error(f"🔧 DEBUG: 예외 상세: {repr(e)}")
            
            logger.error(f"웹사이트 종합 분석 오류: {e}")
            return {
                "error": f"종합 분석 중 오류 발생: {str(e)}",
                "url": url,
                "status": "failed"
            }
    
    async def validate_crawling_quality(self, extracted_data: Dict[str, Any], url: str, 
                                      expected_quality: float = 70.0) -> Dict[str, Any]:
        """
        크롤링 결과 품질 검증
        
        Args:
            extracted_data: 크롤링으로 추출된 데이터
            url: 원본 URL
            expected_quality: 기대 품질 점수
            
        Returns:
            품질 검증 결과
        """
        logger.info(f"크롤링 품질 검증 시작: {url}")
        
        try:
            validation_result = await self.mcp_client.validate_result(
                extracted_data, url, expected_quality
            )
            
            if "error" not in validation_result:
                logger.info(f"품질 검증 완료: {url}, 점수: {validation_result.get('quality_score', 'N/A')}")
            else:
                logger.warning(f"품질 검증 실패: {validation_result['error']}")
            
            return validation_result
            
        except Exception as e:
            logger.error(f"품질 검증 오류: {e}")
            return {
                "error": f"품질 검증 중 오류 발생: {str(e)}",
                "url": url,
                "status": "failed"
            }
    
    async def get_optimal_crawler_for_url(self, url: str, sample_html: str = "") -> str:
        """
        URL에 대한 최적 크롤러 추천
        
        Args:
            url: 분석할 URL
            sample_html: 선택적 HTML 샘플
            
        Returns:
            추천 크롤러 이름 (firecrawl, crawl4ai, playwright, requests)
        """
        try:
            analysis = await self.mcp_client.analyze_site(url, sample_html)
            
            if "error" in analysis:
                logger.warning(f"크롤러 추천 실패, 기본값 사용: {analysis['error']}")
                return "requests"  # 기본값
            
            recommended_crawler = analysis.get("recommended_crawler", "requests")
            logger.info(f"URL {url}에 대한 추천 크롤러: {recommended_crawler}")
            
            return recommended_crawler
            
        except Exception as e:
            logger.error(f"크롤러 추천 오류: {e}")
            return "requests"  # 기본값 