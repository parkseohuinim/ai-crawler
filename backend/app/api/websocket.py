from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict, List
import json
import logging
import asyncio
from datetime import datetime

logger = logging.getLogger(__name__)

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.job_connections: Dict[str, List[str]] = {}  # job_id -> [connection_ids]
    
    async def connect(self, websocket: WebSocket, connection_id: str):
        """WebSocket 연결 수락"""
        await websocket.accept()
        self.active_connections[connection_id] = websocket
        logger.info(f"🔌 WebSocket 연결: {connection_id}")
    
    def disconnect(self, connection_id: str):
        """WebSocket 연결 해제"""
        if connection_id in self.active_connections:
            del self.active_connections[connection_id]
            logger.info(f"🔌 WebSocket 연결 해제: {connection_id}")
        
        # job 연결에서도 제거
        for job_id, conn_ids in self.job_connections.items():
            if connection_id in conn_ids:
                conn_ids.remove(connection_id)
                if not conn_ids:  # 빈 리스트면 job도 제거
                    del self.job_connections[job_id]
                break
    
    async def send_personal_message(self, message: dict, connection_id: str):
        """특정 연결에 메시지 전송"""
        if connection_id in self.active_connections:
            try:
                await self.active_connections[connection_id].send_text(json.dumps(message))
            except Exception as e:
                logger.error(f"❌ 메시지 전송 실패 ({connection_id}): {e}")
                self.disconnect(connection_id)
    
    async def send_job_update(self, message: dict, job_id: str):
        """특정 job을 구독하는 모든 연결에 메시지 전송"""
        if job_id in self.job_connections:
            disconnected = []
            for connection_id in self.job_connections[job_id]:
                if connection_id in self.active_connections:
                    try:
                        await self.active_connections[connection_id].send_text(json.dumps(message))
                    except Exception as e:
                        logger.error(f"❌ Job 업데이트 전송 실패 ({connection_id}): {e}")
                        disconnected.append(connection_id)
                else:
                    disconnected.append(connection_id)
            
            # 끊어진 연결들 정리
            for conn_id in disconnected:
                if conn_id in self.job_connections[job_id]:
                    self.job_connections[job_id].remove(conn_id)
    
    def subscribe_to_job(self, connection_id: str, job_id: str):
        """연결을 특정 job에 구독"""
        if job_id not in self.job_connections:
            self.job_connections[job_id] = []
        
        if connection_id not in self.job_connections[job_id]:
            self.job_connections[job_id].append(connection_id)
            logger.info(f"📡 {connection_id} -> Job {job_id} 구독")

# 전역 연결 매니저
manager = ConnectionManager()

async def send_crawling_progress(job_id: str, step: str, progress: int, message: str = "", extra_data: dict = None):
    """크롤링 진행률 전송"""
    update_message = {
        "type": "progress_update",
        "job_id": job_id,
        "timestamp": datetime.now().isoformat(),
        "step": step,
        "progress": progress,
        "message": message,
        "data": extra_data or {}
    }
    
    await manager.send_job_update(update_message, job_id)
    logger.info(f"📊 Progress Update [{job_id}]: {step} ({progress}%) - {message}")

async def send_crawling_complete(job_id: str, result: dict):
    """크롤링 완료 알림"""
    complete_message = {
        "type": "crawling_complete",
        "job_id": job_id,
        "timestamp": datetime.now().isoformat(),
        "result": result
    }
    
    await manager.send_job_update(complete_message, job_id)
    logger.info(f"✅ Crawling Complete [{job_id}]")

async def send_crawling_error(job_id: str, error: str):
    """크롤링 오류 알림"""
    error_message = {
        "type": "crawling_error",
        "job_id": job_id,
        "timestamp": datetime.now().isoformat(),
        "error": error
    }
    
    await manager.send_job_update(error_message, job_id)
    logger.error(f"❌ Crawling Error [{job_id}]: {error}")

async def websocket_endpoint(websocket: WebSocket, connection_id: str):
    """WebSocket 엔드포인트"""
    await manager.connect(websocket, connection_id)
    
    try:
        while True:
            # 클라이언트로부터 메시지 수신
            data = await websocket.receive_text()
            message = json.loads(data)
            
            # 메시지 타입에 따른 처리
            if message.get("type") == "subscribe":
                job_id = message.get("job_id")
                if job_id:
                    manager.subscribe_to_job(connection_id, job_id)
                    
                    # 구독 확인 메시지 전송
                    await manager.send_personal_message({
                        "type": "subscription_confirmed",
                        "job_id": job_id,
                        "message": f"Job {job_id} 구독 완료"
                    }, connection_id)
            
            elif message.get("type") == "ping":
                # Ping-Pong for connection health check
                await manager.send_personal_message({
                    "type": "pong",
                    "timestamp": datetime.now().isoformat()
                }, connection_id)
                
    except WebSocketDisconnect:
        manager.disconnect(connection_id)
    except Exception as e:
        logger.error(f"❌ WebSocket 오류 ({connection_id}): {e}")
        manager.disconnect(connection_id) 