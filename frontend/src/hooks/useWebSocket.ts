import { useEffect, useRef, useState, useCallback } from 'react';

interface ProgressUpdate {
  type: 'progress_update';
  job_id: string;
  timestamp: string;
  step: string;
  progress: number;
  message: string;
  data: Record<string, unknown>;
}

interface CrawlingComplete {
  type: 'crawling_complete';
  job_id: string;
  timestamp: string;
  result: Record<string, unknown>;
}

interface CrawlingError {
  type: 'crawling_error';
  job_id: string;
  timestamp: string;
  error: string;
}

interface SubscriptionConfirmed {
  type: 'subscription_confirmed';
  job_id: string;
  message: string;
}

interface PongMessage {
  type: 'pong';
  timestamp: string;
}

type WebSocketMessage = ProgressUpdate | CrawlingComplete | CrawlingError | SubscriptionConfirmed | PongMessage;

interface UseWebSocketReturn {
  isConnected: boolean;
  subscribe: (jobId: string) => void;
  onProgressUpdate: (callback: (update: ProgressUpdate) => void) => void;
  onCrawlingComplete: (callback: (result: CrawlingComplete) => void) => void;
  onCrawlingError: (callback: (error: CrawlingError) => void) => void;
  connectionId: string;
}

export const useWebSocket = (): UseWebSocketReturn => {
  const [isConnected, setIsConnected] = useState(false);
  const [connectionId, setConnectionId] = useState('');
  const [isClient, setIsClient] = useState(false);
  
  const wsRef = useRef<WebSocket | null>(null);
  const progressCallbackRef = useRef<((update: ProgressUpdate) => void) | null>(null);
  const completeCallbackRef = useRef<((result: CrawlingComplete) => void) | null>(null);
  const errorCallbackRef = useRef<((error: CrawlingError) => void) | null>(null);
  
  // 클라이언트에서만 connectionId 생성
  useEffect(() => {
    setIsClient(true);
    setConnectionId(Math.random().toString(36).substr(2, 9));
  }, []);
  
  const connect = useCallback(() => {
    // 서버 사이드에서는 실행하지 않음
    if (typeof window === 'undefined' || !isClient || !connectionId) {
      return;
    }
    
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      console.log('🔌 WebSocket 이미 연결됨');
      return;
    }
    
    console.log(`🔌 WebSocket 연결 시도: ${connectionId}`);
    
    try {
      // WebSocket 연결 (백엔드 포트에 맞춤)
      const wsUrl = `ws://localhost:8001/ws/${connectionId}`;
      wsRef.current = new WebSocket(wsUrl);
      
      wsRef.current.onopen = () => {
        console.log('✅ WebSocket 연결 성공');
        setIsConnected(true);
      };
      
      wsRef.current.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data);
          console.log('📨 WebSocket 메시지 수신:', message);
          
          switch (message.type) {
            case 'progress_update':
              progressCallbackRef.current?.(message);
              break;
            case 'crawling_complete':
              completeCallbackRef.current?.(message);
              break;
            case 'crawling_error':
              errorCallbackRef.current?.(message);
              break;
            case 'subscription_confirmed':
              console.log('✅ 구독 확인:', message);
              break;
            case 'pong':
              console.log('🏓 Pong 수신');
              break;
          }
        } catch (error) {
          console.error('❌ WebSocket 메시지 파싱 오류:', error);
        }
      };
      
      wsRef.current.onclose = (event) => {
        console.log('🔌 WebSocket 연결 종료:', event.code, event.reason);
        setIsConnected(false);
        
        // 자동 재연결 (5초 후)
        if (isClient) {
          setTimeout(() => {
            console.log('🔄 WebSocket 자동 재연결 시도...');
            connect();
          }, 5000);
        }
      };
      
      wsRef.current.onerror = (error) => {
        console.error('❌ WebSocket 연결 실패. 백엔드 서버(localhost:8001)가 실행 중인지 확인하세요:', error);
        setIsConnected(false);
      };
    } catch (error) {
      console.error('❌ WebSocket 생성 오류:', error);
      setIsConnected(false);
    }
  }, [connectionId, isClient]);
  
  const subscribe = useCallback((jobId: string) => {
    if (!isClient) return;
    
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      const subscribeMessage = {
        type: 'subscribe',
        job_id: jobId
      };
      
      console.log(`📡 Job 구독: ${jobId}`);
      wsRef.current.send(JSON.stringify(subscribeMessage));
    } else {
      console.warn('⚠️ WebSocket 연결되지 않음 - 구독 실패');
    }
  }, [isClient]);
  
  const onProgressUpdate = useCallback((callback: (update: ProgressUpdate) => void) => {
    progressCallbackRef.current = callback;
  }, []);
  
  const onCrawlingComplete = useCallback((callback: (result: CrawlingComplete) => void) => {
    completeCallbackRef.current = callback;
  }, []);
  
  const onCrawlingError = useCallback((callback: (error: CrawlingError) => void) => {
    errorCallbackRef.current = callback;
  }, []);
  
  // 컴포넌트 마운트 시 연결 (클라이언트에서만)
  useEffect(() => {
    if (!isClient || !connectionId) return;
    
    connect();
    
    // Ping을 주기적으로 전송하여 연결 유지
    const pingInterval = setInterval(() => {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({ type: 'ping' }));
      }
    }, 30000); // 30초마다
    
    return () => {
      clearInterval(pingInterval);
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [connect, isClient, connectionId]);
  
  return {
    isConnected: isClient ? isConnected : false,
    subscribe,
    onProgressUpdate,
    onCrawlingComplete,
    onCrawlingError,
    connectionId: connectionId || 'connecting...'
  };
}; 