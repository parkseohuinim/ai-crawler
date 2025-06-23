'use client';

import { CrawlerInfoProps } from '@/types';
import styles from './CrawlerInfo.module.css';

const getEngineIcon = (engine: string) => {
  switch (engine.toLowerCase()) {
    case 'firecrawl':
      return '🔥';
    case 'crawl4ai':
      return '🤖';
    case 'playwright':
      return '🎭';
    case 'requests':
      return '⚡';
    default:
      return '🕷️';
  }
};

const getEngineDescription = (engine: string) => {
  switch (engine.toLowerCase()) {
    case 'firecrawl':
      return '프리미엄 크롤링 서비스 - 복잡한 SPA 및 안티봇 우회';
    case 'crawl4ai':
      return 'AI 네이티브 크롤링 - 지능형 콘텐츠 추출';
    case 'playwright':
      return '브라우저 자동화 - 정밀한 제어 및 인터랙션';
    case 'requests':
      return '고속 HTTP 크롤링 - 정적 사이트 빠른 처리';
    default:
      return '알 수 없는 엔진';
  }
};

const CrawlerInfo: React.FC<CrawlerInfoProps> = ({ 
  crawlerUsed, 
  processingTime 
}) => {
  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <h4>크롤링 엔진 정보</h4>
      </div>
      
      <div className={styles.content}>
        <div className={styles.engineInfo}>
          <div className={styles.engineIcon}>
            {getEngineIcon(crawlerUsed)}
          </div>
          <div className={styles.engineDetails}>
            <div className={styles.engineName}>
              {crawlerUsed.toUpperCase()}
            </div>
            <div className={styles.engineDescription}>
              {getEngineDescription(crawlerUsed)}
            </div>
          </div>
        </div>
        
        <div className={styles.stats}>
          <div className={styles.statItem}>
            <div className={styles.statIcon}>⏱️</div>
            <div className={styles.statInfo}>
              <div className={styles.statLabel}>처리 시간</div>
              <div className={styles.statValue}>{processingTime}</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default CrawlerInfo; 