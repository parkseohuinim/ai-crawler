'use client';

import { useState, useRef, useEffect } from 'react';
import ChatInput from '@/components/chat/ChatInput';
import MessageList from '@/components/chat/MessageList';
import ProgressIndicator from '@/components/chat/ProgressIndicator';
import JsonPreview from '@/components/results/JsonPreview';
import CrawlerInfo from '@/components/results/CrawlerInfo';
import QualityMetrics from '@/components/results/QualityMetrics';
import DownloadButton from '@/components/download/DownloadButton';
import EngineSelectionInfo from '@/components/EngineSelectionInfo';
import { useWebSocket } from '@/hooks/useWebSocket';
import { generateMessageId, generateJobId } from '@/utils/idGenerator';
import { 
  CrawlResult, 
  Message, 
  ProgressState, 
  BulkResult
} from '@/types';

// 엔진 선택 이유 타입 정의
interface EngineSelectionReason {
  selected_engine: string;
  confidence: number;
  analysis_method: string;
  site_characteristics: {
    site_type: string;
    javascript_level: string;
    javascript_score: number;
    anti_bot_risk: string;
    requires_js: boolean;
  };
  selection_reasons: string[];
  technical_details: {
    mcp_reasoning: string;
    script_count: number;
    content_ratio: number;
    attempted_engines: string[];
    success_on_attempt: number;
  };
  fallback_engines: string[];
}
import styles from './page.module.css';

export default function Home() {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '1',
      type: 'system',
      content: '안녕하세요! 지능형 웹 크롤러입니다. URL을 입력해주세요.\n• 단일 URL: 즉시 크롤링\n• 여러 URL: 자동으로 멀티 크롤링',
      timestamp: new Date().toISOString()
    }
  ]);
  const [isLoading, setIsLoading] = useState(false);
  const [progress, setProgress] = useState<ProgressState>({
    currentStep: '',
    percentage: 0,
    isActive: false,
    steps: []
  });
  const [result, setResult] = useState<CrawlResult | null>(null);
  const [bulkResult, setBulkResult] = useState<BulkResult | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  
  // WebSocket 훅 사용
  const { isConnected, subscribe, onProgressUpdate, onCrawlingComplete, onCrawlingError } = useWebSocket();

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, progress.isActive, bulkResult?.completedUrls]);

  // WebSocket 이벤트 핸들러 설정
  useEffect(() => {
    onProgressUpdate((update) => {
      console.log('📊 Progress Update:', update);
      setProgress({
        currentStep: update.step,
        percentage: update.progress,
        isActive: true,
        steps: [update.message]
      });
    });

    onCrawlingComplete((data) => {
      console.log('✅ Crawling Complete:', data);
      setIsLoading(false);
      setProgress(prev => ({ ...prev, isActive: false }));
      
      // 🔧 벌크 크롤링 완료 처리 - data.result에서 정보 추출
      if (data.result && data.result.status === 'completed' && data.result.results) {
        setBulkResult({
          jobId: data.job_id || generateJobId(),
          totalUrls: (data.result.total_urls as number) || 0,
          completedUrls: (data.result.total_urls as number) || 0,
          successfulUrls: (data.result.successful as number) || 0,
          failedUrls: (data.result.failed as number) || 0,
          results: (data.result.results as CrawlResult[]) || [],
          status: 'completed'
        });
        
        // 벌크 완료 메시지
        const bulkCompleteMessage: Message = {
          id: generateMessageId(),
          type: 'system',
          content: `🎉 멀티 크롤링 완료! 성공: ${data.result.successful}개, 실패: ${data.result.failed}개`,
          timestamp: new Date().toISOString()
        };
        setMessages(prev => [...prev, bulkCompleteMessage]);
        return;
      }
      
      // 기존 단일/선택적 크롤링 완료 처리
      const response = data.result?.response as CrawlResult;
      if (response) {
        // 🔧 통일된 구조에서는 모든 크롤링 결과가 동일한 형태이므로 단순화
        // 🔧 이미 handleSubmit에서 올바르게 처리했으므로 WebSocket 완료는 메시지만 추가
        // setResult는 호출하지 않음 (중복 방지)
        
        // 시스템 메시지 추가
        const systemMessage: Message = {
          id: generateMessageId(),
          type: 'system',
          content: `크롤링이 완료되었습니다! 품질 점수: ${response.metadata?.quality_score || 0}/100`,
          timestamp: new Date().toISOString(),
          metadata: {
            engine: response.metadata?.engine_used || 'unknown',
            quality: response.metadata?.quality_score || 0
          }
        };
        setMessages(prev => [...prev, systemMessage]);
      }
    });

    onCrawlingError((error) => {
      console.error('❌ Crawling Error:', error);
      setIsLoading(false);
      setProgress(prev => ({ ...prev, isActive: false }));
      
      // 🔧 사용자 친화적인 에러 메시지 처리
      let errorContent = error.error || '알 수 없는 오류가 발생했습니다';
      
      // 에러 메시지가 너무 기술적인 경우 간단히 표시
      if (errorContent.length > 100 || errorContent.includes('line ') || errorContent.includes('.py')) {
        errorContent = '페이지를 처리하는 중 오류가 발생했습니다. 잠시 후 다시 시도해보세요.';
      }
      
      const errorMessage: Message = {
        id: generateMessageId(),
        type: 'system',
        content: `❌ ${errorContent}`,
        timestamp: new Date().toISOString(),
        isError: true
      };
      setMessages(prev => [...prev, errorMessage]);
    });
  }, [onProgressUpdate, onCrawlingComplete, onCrawlingError]);

  const handleSubmit = async (input: string, engine?: string) => {
    if (!input.trim() || isLoading) return;
    
    // 사용자 메시지 추가
    const userMessage: Message = {
      id: generateMessageId(),
      type: 'user',
      content: input,
      timestamp: new Date().toISOString()
    };
    setMessages(prev => [...prev, userMessage]);
    
    setIsLoading(true);
    setResult(null);
    setBulkResult(null);
    
    try {
      // 🔧 통합 크롤링 엔드포인트 사용
      const jobId = generateJobId(); // WebSocket 추적용 Job ID 생성
      
      // 🔧 WebSocket 구독 (실시간 진행률 추적)
      subscribe(jobId);
      
      const response = await fetch('http://localhost:8001/api/v1/crawl/unified', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          text: input,  // 자연어 입력 그대로 전송
          clean_text: true,
          engine: engine || null,  // 🔧 엔진 미지정 시 null로 전송하여 MCP 분석 활성화
          job_id: jobId  // WebSocket 추적용 Job ID 전송
        }),
      });

      if (!response.ok) {
        // 🔧 백엔드에서 반환한 에러 메시지 사용
        let errorMessage = '크롤링 요청 처리 중 오류가 발생했습니다';
        try {
          const errorData = await response.json();
          if (errorData.detail) {
            if (typeof errorData.detail === 'string') {
              errorMessage = errorData.detail;
            } else if (errorData.detail.message) {
              errorMessage = errorData.detail.message;
            } else if (errorData.detail.error) {
              errorMessage = errorData.detail.error;
            }
          }
        } catch {
          // JSON 파싱 실패 시 기본 메시지 사용
        }
        throw new Error(errorMessage);
      }

      const data = await response.json();
      console.log('🎯 통합 크롤링 결과:', data);
      
      // 결과 처리 - UnifiedCrawlResponse 구조에 맞게 수정
      // 🔧 최종 결과의 신뢰도를 사용하여 일관성 유지
      const finalConfidence = data.request_type === 'bulk' 
        ? data.metadata.intent_confidence 
        : (data.result?.metadata?.confidence || data.metadata.intent_confidence);
      
      // 의도 분석 결과 메시지
      const intentMessage: Message = {
        id: generateMessageId(),
        type: 'system',
        content: `🧠 의도 분석: ${data.request_type} 크롤링 (신뢰도: ${Math.round(finalConfidence * 100)}%)`,
        timestamp: new Date().toISOString()
      };
      setMessages(prev => [...prev, intentMessage]);
      
      if (data.status === 'complete') {
        // 🔧 통일된 구조: 모든 크롤링 타입이 동일한 CrawlResult 반환
        if (data.request_type === 'bulk') {
          // bulk 크롤링은 완료 시 results 배열을 가짐
          setBulkResult({
            jobId: data.job_id || generateJobId(),
            totalUrls: data.total_urls || 0,
            completedUrls: data.total_urls || 0,
            successfulUrls: data.successful_urls || 0,
            failedUrls: data.failed_urls || 0,
            results: data.results || [],
            status: 'completed'
          });
        } else {
          // single, selective 크롤링은 result 필드를 가짐
          setResult(data.result);
        }
        
        // 성공 메시지
        const successMessage: Message = {
          id: generateMessageId(),
          type: 'system',
          content: `✅ 크롤링 완료! (${data.request_type} 모드)`,
          timestamp: new Date().toISOString()
        };
        setMessages(prev => [...prev, successMessage]);
        
      } else if (data.status === 'processing' && data.request_type === 'bulk') {
        // 🔧 bulk 크롤링 백그라운드 처리 시작
        const bulkStartMessage: Message = {
          id: generateMessageId(),
          type: 'system',
          content: `�� 멀티 크롤링 시작! ${data.total_urls}개 URL을 백그라운드에서 처리 중입니다...`,
          timestamp: new Date().toISOString()
        };
        setMessages(prev => [...prev, bulkStartMessage]);
        
        // 🔧 WebSocket을 통해 실시간 진행률을 추적하므로 여기서는 초기 상태만 설정
        setBulkResult({
          jobId: data.job_id || generateJobId(),
          totalUrls: data.total_urls || 0,
          completedUrls: 0,
          successfulUrls: 0,
          failedUrls: 0,
          results: [],
          status: 'processing'
        });
        
      } else {
        throw new Error(data.error || '크롤링 실패');
      }
      
    } catch (error) {
      console.error('❌ 크롤링 오류:', error);
      
      // 🔧 사용자 친화적인 에러 메시지 생성
      let errorContent = error instanceof Error ? error.message : '알 수 없는 오류';
      
      // 에러 메시지가 너무 기술적인 경우 간단히 표시
      if (errorContent.length > 150 || errorContent.includes('line ') || errorContent.includes('.py')) {
        errorContent = '크롤링 처리 중 문제가 발생했습니다. 잠시 후 다시 시도해보세요.';
      }
      
      const errorMessage: Message = {
        id: generateMessageId(),
        type: 'system',
        content: `❌ ${errorContent}`,
        timestamp: new Date().toISOString(),
        isError: true
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleDownload = () => {
    if (result) {
      // 단일 결과 다운로드
      const dataStr = JSON.stringify(result, null, 2);
      const dataBlob = new Blob([dataStr], { type: 'application/json' });
      
      const url = URL.createObjectURL(dataBlob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `crawl-result-${new Date().toISOString().slice(0, 19).replace(/:/g, '-')}.json`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
    } else if (bulkResult && bulkResult.jobId) {
      // 대량 결과 다운로드 요청
      window.open(`http://localhost:8001/api/v1/jobs/${bulkResult.jobId}/download`, '_blank');
    }
  };

  return (
    <div className={styles.container}>
      <header className={styles.header}>
        <div className={styles.headerContent}>
          <div className={styles.titleSection}>
            <h1>🕷️ Smart Web Crawler</h1>
            <p>MCP 기반 지능형 크롤링 시스템</p>
          </div>
          <div className={styles.statusSection}>
            <div className={`${styles.connectionBadge} ${isConnected ? styles.online : styles.offline}`}>
              <div className={styles.statusIndicator}></div>
              <span className={styles.statusText}>
                {isConnected ? 'LIVE' : 'OFFLINE'}
              </span>
            </div>
          </div>
        </div>
      </header>

      <div className={styles.mainContent}>
        <div className={styles.chatSection}>
          <div className={styles.messageContainer}>
            <MessageList messages={messages} />
            
            {progress.isActive && (
              <div className={styles.progressSection}>
                <ProgressIndicator 
                  progress={progress.percentage} 
                  currentStep={progress.currentStep} 
                />
              </div>
            )}
            
            <div ref={messagesEndRef} />
          </div>
          
          <ChatInput 
            onSubmit={handleSubmit} 
            disabled={isLoading}
          />
        </div>

        {/* 단일 크롤링 결과 */}
        {result && (
          <div className={styles.resultsSection}>
            <div className={styles.resultsHeader}>
              <h2>크롤링 결과</h2>
              <DownloadButton onDownload={handleDownload} />
            </div>
            
            <div className={styles.resultsGrid}>
              <CrawlerInfo 
                crawlerUsed={result.metadata?.engine_used || result.metadata?.crawler_used || 'unknown'}
                processingTime={result.metadata?.processing_time || (result.metadata?.execution_time ? `${result.metadata.execution_time.toFixed(2)}초` : 'N/A')}
              />
              
              <QualityMetrics 
                quality={result.metadata?.quality_score ? `${result.metadata.quality_score}/100` : result.metadata?.content_quality || 'N/A'}
                confidence={result.metadata?.confidence || result.metadata?.extraction_confidence || 0}
              />
            </div>
            
            {/* 엔진 선택 이유 */}
            {result.metadata?.engine_selection_reason && (
              <EngineSelectionInfo reason={result.metadata.engine_selection_reason as EngineSelectionReason} />
            )}
            
            <JsonPreview data={result} />
          </div>
        )}

        {/* 멀티 크롤링 결과 */}
        {bulkResult && (
          <div className={styles.resultsSection}>
            <div className={styles.resultsHeader}>
              <h2>멀티 크롤링 결과</h2>
              <DownloadButton onDownload={handleDownload} />
            </div>
            
            <div className={styles.bulkSummary}>
              <div className={styles.summaryCards}>
                <div className={styles.summaryCard}>
                  <div className={styles.cardIcon}>📊</div>
                  <div className={styles.cardContent}>
                    <div className={styles.cardValue}>{bulkResult.totalUrls}</div>
                    <div className={styles.cardLabel}>총 URL</div>
                  </div>
                </div>
                
                <div className={styles.summaryCard}>
                  <div className={styles.cardIcon}>✅</div>
                  <div className={styles.cardContent}>
                    <div className={styles.cardValue}>{bulkResult.successfulUrls}</div>
                    <div className={styles.cardLabel}>성공</div>
                  </div>
                </div>
                
                <div className={styles.summaryCard}>
                  <div className={styles.cardIcon}>❌</div>
                  <div className={styles.cardContent}>
                    <div className={styles.cardValue}>{bulkResult.failedUrls}</div>
                    <div className={styles.cardLabel}>실패</div>
                  </div>
                </div>
                
                <div className={styles.summaryCard}>
                  <div className={styles.cardIcon}>📈</div>
                  <div className={styles.cardContent}>
                    <div className={styles.cardValue}>
                      {bulkResult.totalUrls > 0 ? Math.round((bulkResult.successfulUrls / bulkResult.totalUrls) * 100) : 0}%
                    </div>
                    <div className={styles.cardLabel}>성공률</div>
                  </div>
                </div>
              </div>
              
              <div className={styles.bulkProgress}>
                <div className={styles.progressLabel}>
                  진행률: {bulkResult.completedUrls}/{bulkResult.totalUrls}
                </div>
                <div className={styles.progressBar}>
                  <div 
                    className={styles.progressFill}
                    style={{ 
                      width: `${bulkResult.totalUrls > 0 ? (bulkResult.completedUrls / bulkResult.totalUrls) * 100 : 0}%` 
                    }}
                  ></div>
                </div>
              </div>
            </div>
            
            {bulkResult.status === 'completed' && bulkResult.results.length > 0 && (
              <>
                <div className={styles.bulkResults}>
                  <h3>상세 결과</h3>
                  <div className={styles.resultsList}>
                    {bulkResult.results.map((result, index) => (
                      <div key={index} className={styles.resultItem}>
                        <div className={styles.resultHeader}>
                          <span className={styles.resultUrl}>{result.url}</span>
                          <span className={`${styles.resultStatus} ${styles[result.status]}`}>
                            {result.status === 'complete' ? '✅' : '❌'}
                          </span>
                        </div>
                        <div className={styles.resultMeta}>
                          <span>제목: {result.title || 'N/A'}</span>
                          <span>품질: {result.metadata?.quality_score || 0}/100</span>
                          <span>엔진: {result.metadata?.engine_used || 'N/A'}</span>
                        </div>
                        
                        {/* 각 URL별 엔진 선택 이유 */}
                        {result.metadata?.engine_selection_reason && (
                          <div className={styles.resultEngineInfo}>
                            <EngineSelectionInfo reason={result.metadata.engine_selection_reason as EngineSelectionReason} />
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
                
                {/* 멀티 크롤링 전체 결과 JSON 프리뷰 */}
                <div className={styles.jsonSection}>
                  <h3>전체 결과 JSON</h3>
                  <JsonPreview data={{
                    summary: {
                      job_id: bulkResult.jobId,
                      total_urls: bulkResult.totalUrls,
                      successful_urls: bulkResult.successfulUrls,
                      failed_urls: bulkResult.failedUrls,
                      success_rate: bulkResult.totalUrls > 0 ? Math.round((bulkResult.successfulUrls / bulkResult.totalUrls) * 100) : 0,
                      status: bulkResult.status
                    },
                    results: bulkResult.results
                  }} />
                </div>
              </>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

