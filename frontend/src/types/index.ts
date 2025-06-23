// 통합 크롤링 시스템 타입 정의

export interface CrawlResult {
  url: string;
  title: string;
  text: string;
  hierarchy: Record<string, unknown>;
  metadata: CrawlMetadata;
  status: string;
  timestamp: string;
  error?: string;
}

export interface CrawlMetadata {
  // 엔진 정보
  engine_used?: string;
  crawler_used?: string;
  
  // 처리시간 정보
  processing_time?: string;
  execution_time?: number;
  
  // 품질 정보
  quality_score?: number;
  content_quality?: string;
  confidence?: number;
  extraction_confidence?: number;
  completeness?: number;
  
  // 전략 정보
  strategy_used?: string;
  
  // 선택적 크롤링 관련
  crawling_mode?: string;
  target_content?: string;
  extraction_type?: string;
  selective_crawling_mode?: boolean;
  extracted_data_available?: boolean;
  extracted_data?: Record<string, unknown>;
  
  // 기타 메타데이터
  http_status?: number;
  content_type?: string;
  content_length?: number;
  text_length?: number;
  timeout_strategy?: string;
  attempted_engines?: string[];
  successful_engine_index?: number;
  total_available_engines?: number;
  
  // MCP 관련
  mcp_quality_score?: number;
  quality_assessment?: Record<string, unknown>;
  mcp_analysis?: Record<string, unknown>;
  used_mcp_intelligence?: boolean;
  
  // 후처리 관련
  post_processing_applied?: boolean;
  original_text_length?: number;
  processed_text_length?: number;
  text_reduction_ratio?: number;
  processing_quality_score?: number;
  processing_timestamp?: string;
  
  // 오류 정보
  error?: string;
  error_type?: string;
  final_error?: string;
  all_engines_failed?: boolean;
  validation_failed?: boolean;
  
  // 기타
  [key: string]: unknown;
}

export interface UnifiedCrawlResponse {
  request_type: 'single' | 'bulk' | 'selective';
  input_text: string;
  status: 'complete' | 'processing' | 'failed';
  
  // 단일 결과 (single, selective)
  result?: CrawlResult;
  
  // 다중 결과 (bulk)
  results?: CrawlResult[];
  total_urls?: number;
  successful_urls?: number;
  failed_urls?: number;
  job_id?: string;
  
  // 공통 메타데이터
  metadata: {
    intent_confidence?: number;
    processing_route?: string;
    url_count?: number;
    background_processing?: boolean;
    processing_type?: string;
    [key: string]: unknown;
  };
  timestamp: string;
  error?: string;
}

export interface Message {
  id: string;
  type: 'user' | 'system';
  content: string;
  timestamp: Date | string;
  isError?: boolean;
  metadata?: {
    engine?: string;
    quality?: number;
  };
}

export interface ProgressState {
  currentStep: string;
  percentage: number;
  isActive: boolean;
  steps: string[];
}

export interface BulkResult {
  jobId: string;
  totalUrls: number;
  completedUrls: number;
  successfulUrls: number;
  failedUrls: number;
  results: CrawlResult[];
  status: 'processing' | 'completed' | 'failed';
}

// WebSocket 이벤트 타입들
export interface ProgressUpdate {
  job_id: string;
  step: string;
  progress: number;
  message: string;
}

export interface CrawlingComplete {
  job_id: string;
  result?: {
    status: string;
    total_urls?: number;
    successful?: number;
    failed?: number;
    results?: CrawlResult[];
    response?: CrawlResult;
  };
}

export interface CrawlingError {
  job_id: string;
  error: string;
}

// 컴포넌트 Props 타입들
export interface CrawlerInfoProps {
  crawlerUsed: string;
  processingTime: string;
}

export interface QualityMetricsProps {
  quality: string;
  confidence: number;
}

export interface JsonPreviewProps {
  data: CrawlResult | BulkCrawlResponse | Record<string, unknown>;
}

export interface BulkCrawlResponse {
  summary: {
    job_id: string;
    total_urls: number;
    successful_urls: number;
    failed_urls: number;
    success_rate: number;
    status: string;
    start_time?: string;
    end_time?: string;
  };
  results: CrawlResult[];
}

export interface DownloadButtonProps {
  onDownload: () => void;
}

export interface ChatInputProps {
  onSubmit: (input: string, engine?: string) => void;
  disabled?: boolean;
}

export interface MessageListProps {
  messages: Message[];
}

export interface ProgressIndicatorProps {
  progress: number;
  currentStep: string;
} 