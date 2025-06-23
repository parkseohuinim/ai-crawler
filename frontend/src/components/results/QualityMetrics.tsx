'use client';

import { QualityMetricsProps } from '@/types';
import styles from './QualityMetrics.module.css';

const getQualityColor = (quality: string) => {
  switch (quality.toLowerCase()) {
    case 'high':
      return '#22c55e';
    case 'medium':
      return '#f59e0b';
    case 'low':
      return '#ef4444';
    default:
      return '#6b7280';
  }
};

const getQualityLabel = (quality: string) => {
  switch (quality.toLowerCase()) {
    case 'high':
      return '높음';
    case 'medium':
      return '보통';
    case 'low':
      return '낮음';
    default:
      return quality;
  }
};

const QualityMetrics: React.FC<QualityMetricsProps> = ({
  quality,
  confidence
}) => {
  const confidencePercentage = Math.round(confidence * 100);

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <h4>품질 지표</h4>
      </div>
      
      <div className={styles.content}>
        <div className={styles.metric}>
          <div className={styles.metricLabel}>콘텐츠 품질</div>
          <div className={styles.qualityBadge} style={{ backgroundColor: getQualityColor(quality) }}>
            {getQualityLabel(quality)}
          </div>
        </div>
        
        <div className={styles.metric}>
          <div className={styles.metricLabel}>추출 신뢰도</div>
          <div className={styles.confidenceContainer}>
            <div className={styles.confidenceBar}>
              <div 
                className={styles.confidenceFill}
                style={{ 
                  width: `${confidencePercentage}%`,
                  backgroundColor: getQualityColor(quality)
                }}
              />
            </div>
            <div className={styles.confidenceText}>
              {confidencePercentage}%
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default QualityMetrics; 