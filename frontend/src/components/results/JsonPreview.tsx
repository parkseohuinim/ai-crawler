'use client';

import { useState } from 'react';
import { CrawlResult, JsonPreviewProps, BulkCrawlResponse } from '@/types';
import styles from './JsonPreview.module.css';

// Type guard functions
const isBulkResponse = (data: CrawlResult | BulkCrawlResponse | Record<string, unknown>): data is BulkCrawlResponse => {
  const hasSummary = data && typeof data === 'object' && 'summary' in data;
  const hasResults = data && typeof data === 'object' && 'results' in data && Array.isArray((data as BulkCrawlResponse).results);
  const hasSummaryJobId = hasSummary && typeof (data as BulkCrawlResponse).summary === 'object' && 'job_id' in (data as BulkCrawlResponse).summary;
  
  console.log('🔍 Type guard 체크:', { hasSummary, hasResults, hasSummaryJobId, data });
  
  return hasSummary && hasResults && hasSummaryJobId;
};

const isCrawlResult = (data: CrawlResult | BulkCrawlResponse | Record<string, unknown>): data is CrawlResult => {
  return data && typeof data === 'object' && 'url' in data && 'title' in data && 'metadata' in data;
};

const JsonPreview: React.FC<JsonPreviewProps> = ({ data }) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const [copied, setCopied] = useState(false);

  // Debug: 받은 데이터 구조 확인
  console.log('🔍 JsonPreview 받은 데이터:', data);
  console.log('🔍 isBulkResponse 결과:', isBulkResponse(data));

  const handleCopyAll = async () => {
    try {
      await navigator.clipboard.writeText(JSON.stringify(data, null, 2));
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  };

  // Render bulk summary preview
  const renderBulkPreview = (bulkData: BulkCrawlResponse) => (
    <div className={styles.previewSection}>
      <div className={styles.summaryGrid}>
        <div className={styles.summaryItem}>
          <strong>작업 ID:</strong> 
          <span className={styles.summaryValue}>{bulkData.summary.job_id}</span>
        </div>
        <div className={styles.summaryItem}>
          <strong>총 URL 수:</strong> 
          <span className={styles.summaryValue}>{bulkData.summary.total_urls}개</span>
        </div>
        <div className={styles.summaryItem}>
          <strong>성공:</strong> 
          <span className={styles.summaryValue}>{bulkData.summary.successful_urls}개</span>
        </div>
        <div className={styles.summaryItem}>
          <strong>실패:</strong> 
          <span className={styles.summaryValue}>{bulkData.summary.failed_urls}개</span>
        </div>
        <div className={styles.summaryItem}>
          <strong>성공률:</strong> 
          <span className={styles.summaryValue}>{bulkData.summary.success_rate.toFixed(1)}%</span>
        </div>
        <div className={styles.summaryItem}>
          <strong>상태:</strong> 
          <span className={styles.summaryValue}>{bulkData.summary.status}</span>
        </div>
      </div>
    </div>
  );

  // Render single result preview  
  const renderSinglePreview = (singleData: CrawlResult) => (
    <div className={styles.previewSection}>
      <div className={styles.summaryGrid}>
        <div className={styles.summaryItem}>
          <strong>URL:</strong> 
          <span className={styles.summaryValue}>{singleData.url}</span>
        </div>
        <div className={styles.summaryItem}>
          <strong>제목:</strong> 
          <span className={styles.summaryValue}>{singleData.title}</span>
        </div>
        <div className={styles.summaryItem}>
          <strong>크롤러:</strong> 
          <span className={styles.summaryValue}>{singleData.metadata?.crawler_used || 'N/A'}</span>
        </div>
        <div className={styles.summaryItem}>
          <strong>처리시간:</strong> 
          <span className={styles.summaryValue}>{singleData.metadata?.processing_time || 'N/A'}</span>
        </div>
      </div>
    </div>
  );

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <h3>JSON 결과</h3>
        <div className={styles.controls}>
          <button
            className={styles.expandButton}
            onClick={() => setIsExpanded(!isExpanded)}
          >
            {isExpanded ? '축소' : '확장'}
          </button>
          <button
            className={styles.copyAllButton}
            onClick={handleCopyAll}
          >
            {copied ? '복사됨!' : 'JSON 복사'}
          </button>
        </div>
      </div>

      <div className={`${styles.jsonContainer} ${isExpanded ? styles.expanded : ''}`}>
        <pre className={styles.jsonContent}>
          {JSON.stringify(data, null, 2)}
        </pre>
      </div>

      {!isExpanded && (
        isBulkResponse(data) ? renderBulkPreview(data) : 
        isCrawlResult(data) ? renderSinglePreview(data) : 
        <div className={styles.previewSection}>
          <div className={styles.summaryItem}>
            <strong>데이터 타입:</strong> 
            <span className={styles.summaryValue}>사용자 정의 객체</span>
          </div>
        </div>
      )}
    </div>
  );
};

export default JsonPreview; 