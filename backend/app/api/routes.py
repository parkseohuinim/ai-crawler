from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from pydantic import BaseModel, HttpUrl
from typing import List, Optional, Dict, Any
import logging
import json
import os
import uuid
from datetime import datetime
import asyncio
from ..crawlers.multi_engine import MultiEngineCrawler
from ..crawlers.base import CrawlStrategy, CrawlResult
from ..utils.natural_language_parser import nl_parser, SelectiveCrawlingIntent
from ..utils.error_formatter import format_crawling_error, get_simple_error_message
# Models are defined in this file directly

# 전역 크롤러 인스턴스는 의존성 주입으로 처리
crawler_instance = None

def set_crawler_instance(instance):
    """크롤러 인스턴스 설정"""
    global crawler_instance
    crawler_instance = instance

logger = logging.getLogger(__name__)

router = APIRouter(tags=["crawler"])

# Request Models
class SingleCrawlRequest(BaseModel):
    url: HttpUrl
    engine: Optional[str] = None  # 특정 엔진 강제 지정
    timeout: Optional[int] = 30
    anti_bot_mode: Optional[bool] = False
    job_id: Optional[str] = None  # WebSocket 진행률 추적용
    clean_text: Optional[bool] = True  # 텍스트 후처리 적용 여부

class BulkCrawlRequest(BaseModel):
    urls: List[HttpUrl]
    max_concurrent: Optional[int] = 5
    timeout: Optional[int] = 30
    clean_text: Optional[bool] = True  # 텍스트 후처리 적용 여부

class SmartCrawlRequest(BaseModel):
    text: str  # 자연어 입력 (URL + 추출 요청)
    timeout: Optional[int] = 30
    clean_text: Optional[bool] = True

# 🎯 통합 요청 모델
class UnifiedCrawlRequest(BaseModel):
    text: str  # 모든 형태의 입력 (URL, 자연어, 멀티 URL 등)
    engine: Optional[str] = None
    timeout: Optional[int] = 30
    clean_text: Optional[bool] = True
    job_id: Optional[str] = None

class CrawlResponse(BaseModel):
    url: str
    title: str
    text: str
    hierarchy: Dict[str, Any]
    metadata: Dict[str, Any]
    status: str
    timestamp: str
    error: Optional[str] = None

class SelectiveCrawlResponse(BaseModel):
    url: str
    target_content: str  # 추출한 콘텐츠 타입
    extracted_data: Dict[str, Any]  # 실제 추출된 데이터
    # 🔧 단일 크롤링과 일관성을 위한 추가 필드
    title: Optional[str] = None  # 페이지 제목
    full_text: Optional[str] = None  # 후처리된 전체 텍스트
    hierarchy: Optional[Dict[str, Any]] = None  # 구조화된 정보
    metadata: Dict[str, Any]
    status: str
    timestamp: str
    error: Optional[str] = None

# 🎯 통합 응답 모델 (모든 크롤링 타입을 포괄)
class UnifiedCrawlResponse(BaseModel):
    request_type: str  # "single", "bulk", "selective"
    input_text: str   # 원본 입력
    status: str       # "complete", "processing", "failed"
    
    # 단일 결과 (single, selective)
    result: Optional[CrawlResponse] = None
    
    # 다중 결과 (bulk)
    results: Optional[List[CrawlResponse]] = None
    total_urls: Optional[int] = None
    successful_urls: Optional[int] = None
    failed_urls: Optional[int] = None
    job_id: Optional[str] = None
    
    # 공통 메타데이터
    metadata: Dict[str, Any]
    timestamp: str
    error: Optional[str] = None

# 진행 중인 작업 추적
active_jobs = {}

@router.post("/crawl/single", response_model=CrawlResponse)
async def crawl_single_url(request: SingleCrawlRequest):
    """단일 URL 크롤링"""
    global crawler_instance
    
    if not crawler_instance or not crawler_instance.is_initialized:
        raise HTTPException(status_code=503, detail="크롤링 시스템이 초기화되지 않았습니다")
    
    url = str(request.url)
    job_id = request.job_id or str(uuid.uuid4())[:8]
    
    logger.info(f"📡 단일 크롤링 요청: {url} [Job: {job_id}]")
    
    # WebSocket 진행률 전송 함수 import
    from ..api.websocket import send_crawling_progress, send_crawling_complete, send_crawling_error
    
    try:
        # 진행률 업데이트: 시작
        await send_crawling_progress(job_id, "initializing", 10, "크롤링 시작 중...")
        
        # 사용자 정의 전략 생성
        from ..crawlers.base import CrawlStrategy
        
        if request.engine:
            # 특정 엔진 강제 지정
            if request.engine not in crawler_instance.engines:
                await send_crawling_error(job_id, f"지원하지 않는 엔진: {request.engine}")
                raise HTTPException(status_code=400, detail=f"지원하지 않는 엔진: {request.engine}")
            strategy = CrawlStrategy(
                engine_priority=[request.engine],
                timeout=request.timeout,
                anti_bot_mode=request.anti_bot_mode
            )
            await send_crawling_progress(job_id, "strategy", 25, f"엔진 설정: {request.engine}")
        else:
            # 자동 전략 선택
            strategy = None
            await send_crawling_progress(job_id, "strategy", 25, "최적 엔진 자동 선택 중...")
        
        # 크롤링 실행
        logger.info(f"🚀 API: crawl_with_strategy 호출 시작 - URL: {url}")
        logger.info(f"🚀 API: 사용자 정의 전략: {strategy.engine_priority if strategy else '자동 선택'}")
        logger.info(f"🚀 API: 크롤러 인스턴스 확인 - engines: {list(crawler_instance.engines.keys())}")
        
        await send_crawling_progress(job_id, "crawling", 50, "웹 페이지 접근 및 데이터 추출 중...")
        
        result = await crawler_instance.crawl_with_strategy(url, strategy)
        
        logger.info(f"🚀 API: crawl_with_strategy 완료 - 결과: {result.status}")
        
        # 🔧 크롤링 실패 시 HTTP 에러 응답
        if result.status == "failed":
            raw_error = result.error or "크롤링 실패 (원인 불명)"
            attempted_engines = result.metadata.get("attempted_engines", [])
            
            # 사용자 친화적인 에러 메시지 생성
            user_friendly_error = format_crawling_error(raw_error, url, attempted_engines)
            simple_error = get_simple_error_message(raw_error)
            
            logger.error(f"❌ 크롤링 실패: {url} - {raw_error}")
            await send_crawling_error(job_id, simple_error)
            
            # 실패 결과도 파일로 저장 (디버깅용)
            result_file = f"results/failed_crawl_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            os.makedirs("results", exist_ok=True)
            
            result_dict = {
                "url": result.url,
                "title": result.title,
                "text": result.text,
                "hierarchy": result.hierarchy,
                "metadata": result.metadata,
                "status": result.status,
                "timestamp": result.timestamp.isoformat(),
                "error": raw_error,  # 원본 에러는 파일에 저장
                "user_error": simple_error  # 사용자 친화적 에러도 저장
            }
            
            with open(result_file, 'w', encoding='utf-8') as f:
                json.dump(result_dict, f, ensure_ascii=False, indent=2)
            
            raise HTTPException(
                status_code=422,  # Unprocessable Entity
                detail={
                    "message": simple_error,  # 사용자 친화적인 메시지
                    "url": url,
                    "error": simple_error,  # 프론트엔드에서 표시할 메시지
                    "detailed_error": user_friendly_error,  # 상세 정보 (필요시)
                    "attempted_engines": attempted_engines,
                    "debug_file": result_file
                }
            )
        
        await send_crawling_progress(job_id, "processing", 80, "데이터 처리 및 품질 분석 중...")
        
        # 후처리 적용
        if request.clean_text:
            from ..utils.text_processor import post_process_crawl_result
            result = post_process_crawl_result(result, clean_text=True)
            logger.info(f"🧹 텍스트 후처리 적용 완료 - 압축률: {result.metadata.get('text_reduction_ratio', 1.0):.2f}")
        
        # 결과 저장 (성공한 경우)
        result_file = f"results/single_crawl_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        os.makedirs("results", exist_ok=True)
        
        result_dict = {
            "url": result.url,
            "title": result.title,
            "text": result.text,
            "hierarchy": result.hierarchy,
            "metadata": result.metadata,
            "status": result.status,
            "timestamp": result.timestamp.isoformat(),
            "error": result.error
        }
        
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump(result_dict, f, ensure_ascii=False, indent=2)
        
        logger.info(f"✅ 단일 크롤링 완료: {url} - 품질: {result.metadata.get('quality_score', 0):.1f}/100")
        
        response = CrawlResponse(
            url=result.url,
            title=result.title,
            text=result.text,
            hierarchy=result.hierarchy,
            metadata=result.metadata,
            status=result.status,
            timestamp=result.timestamp.isoformat(),
            error=result.error
        )
        
        # WebSocket 완료 알림
        await send_crawling_complete(job_id, {
            "status": result.status,
            "quality_score": result.metadata.get('quality_score', 0),
            "engine_used": result.metadata.get('engine_used', 'unknown'),
            "title": result.title,
            "text_length": len(result.text),
            "response": response.dict()
        })
        
        return response
        
    except HTTPException:
        # HTTPException은 그대로 재발생
        raise
    except Exception as e:
        raw_error = str(e)
        simple_error = get_simple_error_message(raw_error)
        
        logger.error(f"❌ 단일 크롤링 실패: {url} - {raw_error}")
        await send_crawling_error(job_id, simple_error)
        raise HTTPException(status_code=500, detail=simple_error)

@router.post("/crawl/bulk")
async def crawl_bulk_urls(request: BulkCrawlRequest, background_tasks: BackgroundTasks):
    """대량 URL 크롤링 (백그라운드 처리)"""
    global crawler_instance
    
    if not crawler_instance or not crawler_instance.is_initialized:
        raise HTTPException(status_code=503, detail="크롤링 시스템이 초기화되지 않았습니다")
    
    urls = [str(url) for url in request.urls]
    job_id = f"bulk_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    logger.info(f"📦 대량 크롤링 요청: {len(urls)}개 URL, 작업 ID: {job_id}")
    
    # 작업 상태 초기화
    active_jobs[job_id] = {
        "status": "started",
        "total_urls": len(urls),
        "completed": 0,
        "success": 0,
        "failed": 0,
        "start_time": datetime.now(),
        "progress": 0
    }
    
    async def process_bulk_crawl():
        """백그라운드에서 대량 크롤링 처리"""
        global crawler_instance, active_jobs
        
        # 🔧 WebSocket 함수들을 내부에서 import
        from ..api.websocket import send_crawling_progress, send_crawling_complete, send_crawling_error
        
        if not crawler_instance or not crawler_instance.is_initialized:
            logger.error(f"❌ 크롤링 시스템이 초기화되지 않음: {job_id}")
            await send_crawling_error(job_id, "크롤링 시스템이 초기화되지 않았습니다")
            return
        
        try:
            await send_crawling_progress(job_id, "starting", 5, f"🚀 {len(urls)}개 URL 크롤링 시작...")
            
            # 개별 URL 크롤링 함수 (진행률 업데이트 포함)
            completed_count = 0
            success_count = 0
            results = []
            
            semaphore = asyncio.Semaphore(request.max_concurrent)
            
            async def crawl_single_with_progress(url: str, index: int) -> CrawlResult:
                nonlocal completed_count, success_count
                
                async with semaphore:
                    try:
                        await send_crawling_progress(
                            job_id, 
                            "crawling", 
                            10 + int((completed_count / len(urls)) * 80),  # 10-90% 범위
                            f"📡 크롤링 중: {url[:50]}{'...' if len(url) > 50 else ''}"
                        )
                        
                        result = await crawler_instance.crawl_with_strategy(url)
                        
                        # 후처리 적용 (요청된 경우)
                        if request.clean_text:
                            from ..utils.text_processor import post_process_crawl_result
                            result = post_process_crawl_result(result, clean_text=True)
                        
                        completed_count += 1
                        if result.status == "complete":
                            success_count += 1
                        
                        # 진행률 업데이트
                        progress = 10 + int((completed_count / len(urls)) * 80)
                        await send_crawling_progress(
                            job_id,
                            "processing",
                            progress,
                            f"✅ 완료: {completed_count}/{len(urls)} (성공: {success_count})"
                        )
                        
                        # 작업 상태 업데이트
                        active_jobs[job_id].update({
                            "completed": completed_count,
                            "success": success_count,
                            "failed": completed_count - success_count,
                            "progress": progress
                        })
                        
                        return result
                        
                    except Exception as e:
                        completed_count += 1
                        logger.error(f"❌ URL 크롤링 실패: {url} - {e}")
                        
                        # 진행률 업데이트 (실패 포함)
                        progress = 10 + int((completed_count / len(urls)) * 80)
                        await send_crawling_progress(
                            job_id,
                            "processing",
                            progress,
                            f"⚠️ 진행: {completed_count}/{len(urls)} (성공: {success_count})"
                        )
                        
                        # 작업 상태 업데이트
                        active_jobs[job_id].update({
                            "completed": completed_count,
                            "success": success_count,
                            "failed": completed_count - success_count,
                            "progress": progress
                        })
                        
                        # 실패한 결과 반환
                        return CrawlResult(
                            url=url,
                            title="",
                            text="",
                            hierarchy={},
                            metadata={"error": str(e)},
                            status="failed",
                            timestamp=datetime.now(),
                            error=str(e)
                        )
            
            # 모든 URL을 병렬로 처리
            tasks = [crawl_single_with_progress(url, i) for i, url in enumerate(urls)]
            results = await asyncio.gather(*tasks)
            
            await send_crawling_progress(job_id, "finalizing", 95, "📊 결과 저장 중...")
            
            # 결과 파일 저장
            result_file = f"results/bulk_crawl_{job_id}.json"
            os.makedirs("results", exist_ok=True)
            
            results_data = []
            
            for result in results:
                result_dict = {
                    "url": result.url,
                    "title": result.title,
                    "text": result.text,
                    "hierarchy": result.hierarchy,
                    "metadata": result.metadata,
                    "status": result.status,
                    "timestamp": result.timestamp.isoformat(),
                    "error": result.error
                }
                results_data.append(result_dict)
            
            # 결과 요약
            summary = {
                "job_id": job_id,
                "total_urls": len(urls),
                "successful": success_count,
                "failed": len(urls) - success_count,
                "success_rate": (success_count / len(urls)) * 100,
                "start_time": active_jobs[job_id]["start_time"].isoformat(),
                "end_time": datetime.now().isoformat(),
                "results": results_data
            }
            
            with open(result_file, 'w', encoding='utf-8') as f:
                json.dump(summary, f, ensure_ascii=False, indent=2)
            
            # 작업 상태 업데이트
            active_jobs[job_id].update({
                "status": "completed",
                "completed": len(urls),
                "success": success_count,
                "failed": len(urls) - success_count,
                "end_time": datetime.now(),
                "result_file": result_file,
                "progress": 100
            })
            
            await send_crawling_progress(job_id, "completed", 100, f"🎉 완료! 성공: {success_count}/{len(urls)}")
            
            logger.info(f"📊 대량 크롤링 완료: {job_id} - 성공률: {(success_count/len(urls)*100):.1f}%")
            
        except Exception as e:
            logger.error(f"💥 대량 크롤링 실패: {job_id} - {e}")
            active_jobs[job_id].update({
                "status": "failed",
                "error": str(e),
                "end_time": datetime.now()
            })
            await send_crawling_error(job_id, f"대량 크롤링 실패: {str(e)}")
    
    # 백그라운드 작업 시작
    background_tasks.add_task(process_bulk_crawl)
    
    return {
        "job_id": job_id,
        "message": f"{len(urls)}개 URL의 대량 크롤링이 시작되었습니다",
        "status": "started",
        "total_urls": len(urls)
    }

@router.get("/jobs/{job_id}/status")
async def get_job_status(job_id: str):
    """작업 진행 상태 조회"""
    if job_id not in active_jobs:
        raise HTTPException(status_code=404, detail="작업을 찾을 수 없습니다")
    
    job_info = active_jobs[job_id].copy()
    
    # datetime 객체를 문자열로 변환 (이미 문자열인 경우 그대로 유지)
    if "start_time" in job_info and hasattr(job_info["start_time"], 'isoformat'):
        job_info["start_time"] = job_info["start_time"].isoformat()
    if "end_time" in job_info and hasattr(job_info["end_time"], 'isoformat'):
        job_info["end_time"] = job_info["end_time"].isoformat()
    
    return job_info

@router.get("/jobs/{job_id}/download")
async def download_job_result(job_id: str):
    """작업 결과 파일 다운로드"""
    if job_id not in active_jobs:
        raise HTTPException(status_code=404, detail="작업을 찾을 수 없습니다")
    
    job_info = active_jobs[job_id]
    
    if job_info["status"] != "completed":
        raise HTTPException(status_code=400, detail="작업이 완료되지 않았습니다")
    
    if "result_file" not in job_info:
        raise HTTPException(status_code=404, detail="결과 파일을 찾을 수 없습니다")
    
    result_file = job_info["result_file"]
    
    if not os.path.exists(result_file):
        raise HTTPException(status_code=404, detail="결과 파일이 존재하지 않습니다")
    
    return FileResponse(
        path=result_file,
        filename=f"crawl_results_{job_id}.json",
        media_type="application/json"
    )

@router.get("/jobs/{job_id}/results")
async def get_job_results(job_id: str):
    """작업 결과 데이터 조회 (JSON 형태)"""
    if job_id not in active_jobs:
        raise HTTPException(status_code=404, detail="작업을 찾을 수 없습니다")
    
    job_info = active_jobs[job_id]
    
    if job_info["status"] != "completed":
        raise HTTPException(status_code=400, detail="작업이 완료되지 않았습니다")
    
    if "result_file" not in job_info:
        raise HTTPException(status_code=404, detail="결과 파일을 찾을 수 없습니다")
    
    result_file = job_info["result_file"]
    
    if not os.path.exists(result_file):
        raise HTTPException(status_code=404, detail="결과 파일이 존재하지 않습니다")
    
    try:
        with open(result_file, 'r', encoding='utf-8') as f:
            file_data = json.load(f)
        
        # 프론트엔드가 기대하는 구조로 변환
        formatted_data = {
            "summary": {
                "job_id": file_data.get("job_id"),
                "total_urls": file_data.get("total_urls"),
                "successful_urls": file_data.get("successful"),
                "failed_urls": file_data.get("failed"),
                "success_rate": file_data.get("success_rate"),
                "status": "completed",
                "start_time": file_data.get("start_time"),
                "end_time": file_data.get("end_time")
            },
            "results": file_data.get("results", [])
        }
        
        return formatted_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"결과 파일 읽기 실패: {str(e)}")

@router.get("/engines/status")
async def get_engines_status():
    """모든 크롤링 엔진 상태 조회"""
    global crawler_instance
    
    if not crawler_instance:
        raise HTTPException(status_code=503, detail="크롤링 시스템이 초기화되지 않았습니다")
    
    status = await crawler_instance.get_engine_status()
    return status

@router.get("/jobs/active")
async def get_active_jobs():
    """현재 활성 작업 목록 조회"""
    active_job_list = []
    
    for job_id, job_info in active_jobs.items():
        job_copy = job_info.copy()
        
        # datetime 객체를 문자열로 변환 (이미 문자열인 경우 그대로 유지)
        if "start_time" in job_copy and hasattr(job_copy["start_time"], 'isoformat'):
            job_copy["start_time"] = job_copy["start_time"].isoformat()
        if "end_time" in job_copy and hasattr(job_copy["end_time"], 'isoformat'):
            job_copy["end_time"] = job_copy["end_time"].isoformat()
        
        job_copy["job_id"] = job_id
        active_job_list.append(job_copy)
    
    return {
        "total_jobs": len(active_job_list),
        "jobs": active_job_list
    }

@router.delete("/jobs/{job_id}")
async def cancel_job(job_id: str):
    """작업 취소 (진행 중인 작업은 완료까지 기다림)"""
    if job_id not in active_jobs:
        raise HTTPException(status_code=404, detail="작업을 찾을 수 없습니다")
    
    job_info = active_jobs[job_id]
    
    if job_info["status"] in ["completed", "failed"]:
        # 완료된 작업은 기록에서 제거
        del active_jobs[job_id]
        return {"message": f"작업 {job_id}가 제거되었습니다"}
    else:
        return {"message": f"작업 {job_id}는 진행 중이므로 완료 후 제거됩니다"}

@router.post("/test/simple")
async def test_simple_crawl():
    """간단한 테스트 크롤링"""
    test_url = "https://httpbin.org/html"
    
    request = SingleCrawlRequest(url=test_url)
    result = await crawl_single_url(request)
    
    return {
        "message": "테스트 크롤링 완료",
        "test_url": test_url,
        "result_summary": {
            "status": result.status,
            "title": result.title,
            "text_length": len(result.text),
            "crawler_used": result.metadata.get("crawler_used"),
            "quality_score": result.metadata.get("quality_score")
        }
    }

@router.post("/crawl/smart", response_model=SelectiveCrawlResponse)
async def smart_natural_crawl(request: SmartCrawlRequest):
    """자연어 기반 스마트 크롤링 (선택적 추출)"""
    global crawler_instance
    
    if not crawler_instance or not crawler_instance.is_initialized:
        raise HTTPException(status_code=503, detail="크롤링 시스템이 초기화되지 않았습니다")
    
    job_id = str(uuid.uuid4())[:8]
    logger.info(f"🧠 스마트 크롤링 요청: {request.text} [Job: {job_id}]")
    
    # WebSocket 진행률 전송 함수 import
    from ..api.websocket import send_crawling_progress, send_crawling_complete, send_crawling_error
    
    try:
        # 1단계: 자연어 파싱
        await send_crawling_progress(job_id, "parsing", 15, "🔍 자연어 분석 중...")
        
        intent = nl_parser.parse_selective_request(request.text)
        validation = nl_parser.validate_intent(intent)
        
        if not validation["is_valid"]:
            error_msg = validation["message"]
            await send_crawling_error(job_id, error_msg)
            raise HTTPException(status_code=400, detail=error_msg)
        
        # 피드백 메시지
        await send_crawling_progress(
            job_id, "intent_confirmed", 30, 
            validation["message"]
        )
        
        # 2단계: URL 크롤링
        url = intent.urls[0]  # 첫 번째 URL 사용
        await send_crawling_progress(
            job_id, "crawling", 50, 
            f"📡 크롤링 시작: {url}"
        )
        
        # 기본 크롤링 실행
        result = await crawler_instance.crawl_with_strategy(
            url=intent.urls[0],
            custom_strategy=None  # 자동 전략 선택
        )
        
        if not result or result.status != "complete":
            error_msg = f"크롤링 실패: {result.error if result else '알 수 없는 오류'}"
            await send_crawling_error(job_id, error_msg)
            raise HTTPException(status_code=500, detail=error_msg)
        
        # 🧹 후처리 적용 (단일/멀티 크롤링과 동일하게)
        if request.clean_text:
            await send_crawling_progress(
                job_id, "post_processing", 65, 
                "🧹 텍스트 후처리 적용 중..."
            )
            
            from ..utils.text_processor import post_process_crawl_result
            result = post_process_crawl_result(result, clean_text=True)
            logger.info(f"🧹 스마트 크롤링 후처리 완료 - 압축률: {result.metadata.get('text_reduction_ratio', 1.0):.2f}")
        
        # 3단계: 선택적 콘텐츠 추출
        await send_crawling_progress(
            job_id, "extracting", 75, 
            f"🎯 '{intent.target_content}' 추출 중..."
        )
        
        # MCP 클라이언트를 통한 선택적 추출
        extraction_result = await crawler_instance.mcp_client.extract_selective_content(
            html_content=result.text,  # 크롤링된 내용
            target_content=intent.target_content,
            url=url
        )
        
        if "error" in extraction_result:
            error_msg = f"추출 실패: {extraction_result['error']}"
            await send_crawling_error(job_id, error_msg)
            raise HTTPException(status_code=500, detail=error_msg)
        
        # 4단계: 결과 저장
        await send_crawling_progress(job_id, "saving", 90, "💾 결과 저장 중...")
        
        result_file = f"results/smart_crawl_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        os.makedirs("results", exist_ok=True)
        
        response_data = SelectiveCrawlResponse(
            url=url,
            target_content=intent.target_content,
            extracted_data=extraction_result.get("extracted_data", {}),
            # 🔧 단일 크롤링과 일관성을 위한 추가 정보
            title=result.title,
            full_text=result.text,  # 후처리된 전체 텍스트
            hierarchy=result.hierarchy,
            metadata={
                # 🔧 크롤링 엔진 정보 - result.metadata에서 올바르게 가져오기
                "engine_used": result.metadata.get("engine_used") or result.metadata.get("crawler_used", "unknown"),
                "crawler_used": result.metadata.get("crawler_used", "unknown"),
                
                # 🔧 처리시간 정보
                "processing_time": result.metadata.get("processing_time", "N/A"),
                "execution_time": result.metadata.get("execution_time"),
                
                # 🔧 품질 정보 - extraction_result와 original_crawling_metadata에서 최적값 선택
                "quality_score": result.metadata.get("quality_score") or extraction_result.get("quality_score", 0),
                "content_quality": result.metadata.get("content_quality", "medium"),
                "confidence": result.metadata.get("confidence") or result.metadata.get("extraction_confidence") or (result.metadata.get("quality_score", 0) / 100.0) or 0.5,
                "extraction_confidence": result.metadata.get("extraction_confidence") or result.metadata.get("confidence") or (result.metadata.get("quality_score", 0) / 100.0) or 0.5,
                
                # 🔧 선택적 크롤링 특화 정보
                "crawling_mode": "selective",
                "target_content": intent.target_content,
                "extraction_type": intent.extraction_type,
                "selective_crawling_mode": True,
                "extracted_data": extraction_result.get("extracted_data", {}),
                
                # 🔧 기타 메타데이터
                "intent_confidence": intent.confidence,
                "raw_request": intent.raw_request,
                "text_length": len(result.text),
                "post_processing_applied": request.clean_text,
                
                # 🔧 원본 크롤링 메타데이터 포함
                "original_crawling_metadata": result.metadata
            },
            status="complete",
            timestamp=datetime.now().isoformat()
        )
        
        # 결과 파일 저장
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump(response_data.dict(), f, ensure_ascii=False, indent=2)
        
        # 완료 알림
        await send_crawling_complete(job_id, {
            "status": "complete",
            "target_content": intent.target_content,
            "extraction_quality": extraction_result.get("quality_score", 0.0),
            "url": url,
            "response": response_data.dict()
        })
        
        logger.info(f"✅ 스마트 크롤링 완료: {url} -> {intent.target_content}")
        return response_data
        
    except HTTPException:
        # 이미 처리된 HTTP 예외는 다시 발생
        raise
    except Exception as e:
        logger.error(f"❌ 스마트 크롤링 실패: {request.text} - {e}")
        await send_crawling_error(job_id, str(e))
        raise HTTPException(status_code=500, detail=f"스마트 크롤링 실패: {str(e)}")

@router.post("/parse/intent")
async def parse_natural_language_intent(request: SmartCrawlRequest):
    """자연어 의도 파싱 (테스트용)"""
    try:
        intent = nl_parser.parse_selective_request(request.text)
        validation = nl_parser.validate_intent(intent)
        
        return {
            "raw_text": request.text,
            "parsed_intent": {
                "urls": intent.urls,
                "target_content": intent.target_content,
                "confidence": intent.confidence,
                "extraction_type": intent.extraction_type
            },
            "validation": validation,
            "suggestions": validation.get("suggestions", [])
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"의도 파싱 실패: {str(e)}")

# 🎯 통합 크롤링 엔드포인트
@router.post("/crawl/unified", response_model=UnifiedCrawlResponse)
async def unified_crawl(request: UnifiedCrawlRequest):
    """
    통합 크롤링 엔드포인트
    모든 형태의 입력을 받아서 의도를 분석하고 적절한 처리 방식으로 라우팅
    """
    global crawler_instance
    
    if not crawler_instance or not crawler_instance.is_initialized:
        raise HTTPException(status_code=503, detail="크롤링 시스템이 초기화되지 않았습니다")
    
    job_id = request.job_id or str(uuid.uuid4())[:8]
    logger.info(f"🎯 통합 크롤링 요청: {request.text} [Job: {job_id}]")
    
    # WebSocket 진행률 전송 함수 import
    from ..api.websocket import send_crawling_progress, send_crawling_complete, send_crawling_error
    
    try:
        # 1단계: 통합 의도 분석
        await send_crawling_progress(job_id, "analyzing", 10, "🧠 입력 분석 중...")
        
        intent = nl_parser.analyze_unified_intent(request.text)
        
        logger.info(f"🎯 의도 분석 결과: {intent.request_type} (신뢰도: {intent.confidence:.2f})")
        
        # 2단계: 의도에 따른 라우팅
        await send_crawling_progress(
            job_id, "routing", 20, 
            f"📍 처리 방식 결정: {intent.request_type}"
        )
        
        if intent.request_type == "invalid":
            error_msg = intent.metadata.get("error", "유효하지 않은 요청입니다")
            await send_crawling_error(job_id, error_msg)
            raise HTTPException(status_code=400, detail=error_msg)
        
        elif intent.request_type == "single":
            # 단일 URL 크롤링으로 라우팅
            result = await _handle_single_crawl_internal(
                intent.urls[0], request.engine, request.timeout, 
                request.clean_text, job_id
            )
            
            return UnifiedCrawlResponse(
                request_type="single",
                input_text=request.text,
                result=result,
                metadata={
                    "intent_confidence": intent.confidence,
                    "processing_route": "single_crawl",
                    **intent.metadata
                },
                status="complete",
                timestamp=datetime.now().isoformat()
            )
        
        elif intent.request_type == "bulk":
            # 멀티 URL 크롤링으로 라우팅 (백그라운드 처리)
            # 🔧 백그라운드 처리 시작만 하고 즉시 응답
            await _handle_bulk_crawl_internal(
                intent.urls, request.timeout, request.clean_text, job_id
            )
            
            return UnifiedCrawlResponse(
                request_type="bulk",
                input_text=request.text,
                results=None,  # 백그라운드 처리 중이므로 None
                total_urls=len(intent.urls),
                successful_urls=0,  # 아직 처리 중
                failed_urls=0,      # 아직 처리 중
                job_id=job_id,
                metadata={
                    "intent_confidence": intent.confidence,
                    "processing_route": "bulk_crawl",
                    "url_count": len(intent.urls),
                    "background_processing": True,
                    **intent.metadata
                },
                status="processing",  # 🔧 백그라운드 처리 중이므로 processing
                timestamp=datetime.now().isoformat()
            )
        
        elif intent.request_type == "selective":
            # 선택적 크롤링으로 라우팅
            selective_result = await _handle_selective_crawl_internal(
                intent.urls[0], intent.target_content, request.timeout,
                request.clean_text, job_id
            )
            
            return UnifiedCrawlResponse(
                request_type="selective",
                input_text=request.text,
                result=selective_result,
                metadata={
                    "intent_confidence": intent.confidence,
                    "processing_route": "selective_crawl",
                    "target_content": intent.target_content,
                    **intent.metadata
                },
                status="complete",
                timestamp=datetime.now().isoformat()
            )
        
        elif intent.request_type == "search":
            # 검색 크롤링 (미래 기능)
            await send_crawling_error(
                job_id, 
                f"'{intent.platform}'에서 '{intent.search_query}' 검색 기능은 아직 구현되지 않았습니다"
            )
            raise HTTPException(
                status_code=501, 
                detail=f"플랫폼 검색 기능은 아직 구현되지 않았습니다. (요청: {intent.platform} - {intent.search_query})"
            )
        
        else:
            # 알 수 없는 요청 타입
            await send_crawling_error(job_id, f"지원하지 않는 요청 타입: {intent.request_type}")
            raise HTTPException(status_code=400, detail=f"지원하지 않는 요청 타입: {intent.request_type}")
        
    except HTTPException:
        # 이미 처리된 HTTP 예외는 다시 발생
        raise
    except Exception as e:
        raw_error = str(e)
        simple_error = get_simple_error_message(raw_error)
        
        logger.error(f"❌ 통합 크롤링 실패: {request.text} - {raw_error}")
        await send_crawling_error(job_id, simple_error)
        raise HTTPException(status_code=500, detail=simple_error)

# 🔧 내부 처리 함수들 (기존 로직 재사용)
async def _handle_single_crawl_internal(
    url: str, engine: Optional[str], timeout: int, 
    clean_text: bool, job_id: str
) -> CrawlResponse:
    """단일 크롤링 내부 처리"""
    # 기존 crawl_single_url 로직 재사용
    single_request = SingleCrawlRequest(
        url=url, engine=engine, timeout=timeout, 
        clean_text=clean_text, job_id=job_id
    )
    
    try:
        return await crawl_single_url(single_request)
    except HTTPException as e:
        # HTTPException의 경우 상세 정보를 포함한 응답 생성
        if e.status_code == 422:  # 크롤링 실패
            error_detail = e.detail
            if isinstance(error_detail, dict):
                error_msg = error_detail.get("error", "크롤링 실패")
                attempted_engines = error_detail.get("attempted_engines", [])
            else:
                error_msg = str(error_detail)
                attempted_engines = []
            
            # 실패 응답을 CrawlResponse 형태로 변환
            return CrawlResponse(
                url=url,
                title="",
                text="",
                hierarchy={},
                metadata={
                    "error": error_msg,
                    "attempted_engines": attempted_engines,
                    "all_engines_failed": True,
                    "failure_reason": "crawling_failed"
                },
                status="failed",
                timestamp=datetime.now().isoformat(),
                error=error_msg  # 이미 포맷된 사용자 친화적 메시지
            )
        else:
            # 다른 HTTP 에러는 그대로 재발생
            raise

async def _handle_bulk_crawl_internal(
    urls: List[str], timeout: int, clean_text: bool, job_id: str
) -> None:
    """멀티 크롤링 내부 처리 - 백그라운드 처리만 시작"""
    global crawler_instance, active_jobs
    
    if not crawler_instance or not crawler_instance.is_initialized:
        raise HTTPException(status_code=503, detail="크롤링 시스템이 초기화되지 않았습니다")
    
    # WebSocket 진행률 전송 함수 import
    from ..api.websocket import send_crawling_progress, send_crawling_complete, send_crawling_error
    
    # 작업 상태 초기화
    active_jobs[job_id] = {
        "status": "processing",
        "total_urls": len(urls),
        "completed": 0,
        "success": 0,
        "failed": 0,
        "results": [],
        "start_time": datetime.now().isoformat(),
        "urls": urls
    }
    
    logger.info(f"🚀 통합 대량 크롤링 시작: {len(urls)}개 URL [Job: {job_id}]")
    
    # 백그라운드 작업 정의
    async def process_bulk_crawl():
        """백그라운드 대량 크롤링 처리"""
        logger.info(f"🔥 process_bulk_crawl 시작: {job_id}")
        try:
            logger.info(f"📡 WebSocket 진행률 전송 시도: {job_id}")
            await send_crawling_progress(job_id, "starting", 5, f"🚀 {len(urls)}개 URL 크롤링 시작")
            
            # 동시 크롤링 함수
            async def crawl_single_with_progress(url: str, index: int):
                try:
                    logger.info(f"🔍 개별 크롤링 시작: {url} [{index+1}/{len(urls)}]")
                    
                    # 개별 크롤링 실행
                    single_request = SingleCrawlRequest(
                        url=url, 
                        timeout=timeout,
                        clean_text=clean_text,
                        job_id=f"{job_id}-{index}"  # 개별 작업 ID
                    )
                    
                    result = await crawl_single_url(single_request)
                    
                    # 성공 처리
                    active_jobs[job_id]["completed"] += 1
                    active_jobs[job_id]["success"] += 1
                    active_jobs[job_id]["results"].append(result.dict())
                    
                    # 진행률 업데이트
                    progress = int((active_jobs[job_id]["completed"] / len(urls)) * 100)
                    await send_crawling_progress(
                        job_id, "processing", progress,
                        f"✅ {active_jobs[job_id]['completed']}/{len(urls)} 완료"
                    )
                    
                    logger.info(f"✅ 개별 크롤링 성공: {url}")
                    return result
                    
                except Exception as e:
                    # 실패 처리
                    active_jobs[job_id]["completed"] += 1
                    active_jobs[job_id]["failed"] += 1
                    
                    error_result = CrawlResponse(
                        url=url,
                        title="",
                        text="",
                        hierarchy={},
                        metadata={"error": str(e)},
                        status="failed",
                        timestamp=datetime.now().isoformat(),
                        error=str(e)
                    )
                    active_jobs[job_id]["results"].append(error_result.dict())
                    
                    # 진행률 업데이트
                    progress = int((active_jobs[job_id]["completed"] / len(urls)) * 100)
                    await send_crawling_progress(
                        job_id, "processing", progress,
                        f"❌ {active_jobs[job_id]['completed']}/{len(urls)} 완료 (실패: {url})"
                    )
                    
                    logger.error(f"❌ 개별 크롤링 실패: {url} - {e}")
                    return error_result
            
            # 동시 실행 (최대 3개)
            semaphore = asyncio.Semaphore(3)
            
            async def crawl_with_semaphore(url: str, index: int):
                async with semaphore:
                    return await crawl_single_with_progress(url, index)
            
            # 모든 URL 동시 크롤링
            tasks = [crawl_with_semaphore(url, i) for i, url in enumerate(urls)]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 파일로 결과 저장
            await send_crawling_progress(job_id, "saving", 95, "💾 결과 파일 저장 중...")
            
            result_file = f"results/unified_bulk_crawl_{job_id}.json"
            os.makedirs("results", exist_ok=True)
            
            # 결과 요약 생성
            summary = {
                "job_id": job_id,
                "crawl_type": "unified_bulk",
                "total_urls": len(urls),
                "successful": active_jobs[job_id]["success"],
                "failed": active_jobs[job_id]["failed"],
                "success_rate": (active_jobs[job_id]["success"] / len(urls)) * 100,
                "start_time": active_jobs[job_id]["start_time"],
                "end_time": datetime.now().isoformat(),
                "results": active_jobs[job_id]["results"]
            }
            
            with open(result_file, 'w', encoding='utf-8') as f:
                json.dump(summary, f, ensure_ascii=False, indent=2)
            
            # 완료 처리
            active_jobs[job_id]["status"] = "completed"
            active_jobs[job_id]["end_time"] = datetime.now().isoformat()
            active_jobs[job_id]["result_file"] = result_file
            
            logger.info(f"💾 통합 멀티 크롤링 결과 저장: {result_file}")
            
            # 최종 완료 알림
            await send_crawling_complete(job_id, {
                "status": "completed",
                "total_urls": len(urls),
                "successful": active_jobs[job_id]["success"],
                "failed": active_jobs[job_id]["failed"],
                "results": active_jobs[job_id]["results"],
                "result_file": result_file
            })
            
            logger.info(f"🎉 통합 대량 크롤링 완료: {job_id} (성공: {active_jobs[job_id]['success']}, 실패: {active_jobs[job_id]['failed']})")
            
        except Exception as e:
            # 전체 작업 실패
            active_jobs[job_id]["status"] = "failed"
            active_jobs[job_id]["error"] = str(e)
            active_jobs[job_id]["end_time"] = datetime.now().isoformat()
            
            await send_crawling_error(job_id, f"대량 크롤링 실패: {str(e)}")
            logger.error(f"💥 통합 대량 크롤링 전체 실패: {job_id} - {e}")
    
    # 백그라운드 작업 시작 (asyncio.ensure_future 사용)
    import asyncio
    asyncio.ensure_future(process_bulk_crawl())

async def _handle_selective_crawl_internal(
    url: str, target_content: str, timeout: int, 
    clean_text: bool, job_id: str
) -> CrawlResponse:
    """선택적 크롤링 내부 처리 - 통일된 CrawlResponse 반환"""
    # 🔧 job_id를 포함한 스마트 크롤링 요청 생성
    smart_request = SmartCrawlRequest(
        text=f"{url}의 {target_content} 추출해줘",
        timeout=timeout, 
        clean_text=clean_text
    )
    
    # 🔧 기존 smart_natural_crawl 로직을 직접 호출하되 job_id 전달
    global crawler_instance
    
    if not crawler_instance or not crawler_instance.is_initialized:
        raise HTTPException(status_code=503, detail="크롤링 시스템이 초기화되지 않았습니다")
    
    # WebSocket 진행률 전송 함수 import
    from ..api.websocket import send_crawling_progress, send_crawling_complete, send_crawling_error
    
    try:
        # 1단계: 자연어 파싱
        await send_crawling_progress(job_id, "parsing", 30, "🔍 자연어 의도 분석 중...")
        
        intent = nl_parser.parse_selective_request(smart_request.text)
        validation = nl_parser.validate_intent(intent)
        
        if not validation["is_valid"]:
            error_msg = validation["message"]
            await send_crawling_error(job_id, error_msg)
            raise HTTPException(status_code=400, detail=error_msg)
        
        # 2단계: 크롤링 실행
        await send_crawling_progress(job_id, "crawling", 50, f"🕷️ {url} 크롤링 중...")
        
        result = await crawler_instance.crawl_with_strategy(
            url=intent.urls[0],
            custom_strategy=None  # 자동 전략 선택
        )
        
        if not result or result.status != "complete":
            error_msg = f"크롤링 실패: {result.error if result else '알 수 없는 오류'}"
            await send_crawling_error(job_id, error_msg)
            raise HTTPException(status_code=500, detail=error_msg)
        
        # 3단계: 선택적 추출
        await send_crawling_progress(job_id, "extracting", 70, f"🎯 '{intent.target_content}' 추출 중...")
        
        # MCP 클라이언트를 통한 선택적 추출
        extraction_result = await crawler_instance.mcp_client.extract_selective_content(
            html_content=result.text,  # 크롤링된 내용
            target_content=intent.target_content,
            url=url
        )
        
        if "error" in extraction_result:
            error_msg = f"추출 실패: {extraction_result['error']}"
            await send_crawling_error(job_id, error_msg)
            raise HTTPException(status_code=500, detail=error_msg)
        
        # 4단계: 후처리 적용
        await send_crawling_progress(job_id, "processing", 80, "🧹 텍스트 후처리 중...")
        
        if clean_text:
            from ..utils.text_processor import post_process_crawl_result
            result = post_process_crawl_result(result, clean_text=True)
        
        # 5단계: 통일된 CrawlResponse 생성
        await send_crawling_progress(job_id, "saving", 90, "💾 결과 저장 중...")
        
        # 🔧 통일된 CrawlResponse 형태로 반환
        response_data = CrawlResponse(
            url=url,
            title=result.title,
            text=result.text,  # 후처리된 전체 텍스트
            hierarchy=result.hierarchy,
            metadata={
                # 🔧 크롤링 엔진 정보 - result.metadata에서 올바르게 가져오기
                "engine_used": result.metadata.get("engine_used") or result.metadata.get("crawler_used", "unknown"),
                "crawler_used": result.metadata.get("crawler_used", "unknown"),
                
                # 🔧 처리시간 정보
                "processing_time": result.metadata.get("processing_time", "N/A"),
                "execution_time": result.metadata.get("execution_time"),
                
                # 🔧 품질 정보 - extraction_result와 original_crawling_metadata에서 최적값 선택
                "quality_score": result.metadata.get("quality_score") or extraction_result.get("quality_score", 0),
                "content_quality": result.metadata.get("content_quality", "medium"),
                # 🔧 의도 분석 신뢰도와 크롤링 신뢰도를 결합하여 최종 신뢰도 계산
                "confidence": min(
                    intent.confidence,  # 의도 분석 신뢰도
                    result.metadata.get("confidence") or result.metadata.get("extraction_confidence") or (result.metadata.get("quality_score", 0) / 100.0) or 0.5  # 크롤링 신뢰도
                ),
                "extraction_confidence": result.metadata.get("extraction_confidence") or result.metadata.get("confidence") or (result.metadata.get("quality_score", 0) / 100.0) or 0.5,
                
                # 🔧 선택적 크롤링 특화 정보
                "crawling_mode": "selective",
                "target_content": intent.target_content,
                "extraction_type": intent.extraction_type,
                "selective_crawling_mode": True,
                "extracted_data": extraction_result.get("extracted_data", {}),
                
                # 🔧 기타 메타데이터
                "intent_confidence": intent.confidence,
                "raw_request": intent.raw_request,
                "text_length": len(result.text),
                "post_processing_applied": clean_text,
                
                # 🔧 원본 크롤링 메타데이터 포함
                "original_crawling_metadata": result.metadata
            },
            status="complete",
            timestamp=datetime.now().isoformat()
        )
        
        # 결과 파일 저장
        result_file = f"results/selective_crawl_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        os.makedirs("results", exist_ok=True)
        
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump(response_data.dict(), f, ensure_ascii=False, indent=2)
        
        # 완료 알림
        await send_crawling_complete(job_id, {
            "status": "complete",
            "target_content": intent.target_content,
            "extraction_quality": extraction_result.get("quality_score", 0.0),
            "url": url,
            "response": response_data.dict()
        })
        
        logger.info(f"✅ 선택적 크롤링 완료: {url} -> {intent.target_content}")
        return response_data
        
    except HTTPException:
        # 이미 처리된 HTTP 예외는 다시 발생
        raise
    except Exception as e:
        logger.error(f"❌ 선택적 크롤링 실패: {smart_request.text} - {e}")
        await send_crawling_error(job_id, str(e))
        raise HTTPException(status_code=500, detail=f"선택적 크롤링 실패: {str(e)}") 