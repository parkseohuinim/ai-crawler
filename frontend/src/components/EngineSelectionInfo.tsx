import React, { useState } from 'react';
import styles from './EngineSelectionInfo.module.css';

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

interface EngineSelectionInfoProps {
  reason: EngineSelectionReason;
}

const EngineSelectionInfo: React.FC<EngineSelectionInfoProps> = ({ reason }) => {
  const [isExpanded, setIsExpanded] = useState(false);

  const getEngineIcon = (engine: string) => {
    switch (engine) {
      case 'crawl4ai': return '🤖';
      case 'firecrawl': return '🔥';
      case 'playwright': return '🎭';
      case 'requests': return '📡';
      default: return '⚙️';
    }
  };

  const getEngineDescription = (engine: string) => {
    switch (engine) {
      case 'crawl4ai': return 'AI 기반 크롤러';
      case 'firecrawl': return '프리미엄 서비스';
      case 'playwright': return '브라우저 자동화';
      case 'requests': return 'HTTP 크롤러';
      default: return '크롤링 엔진';
    }
  };

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.8) return styles.confidenceHigh;
    if (confidence >= 0.6) return styles.confidenceMedium;
    return styles.confidenceLow;
  };

  const getRiskColor = (risk: string) => {
    switch (risk) {
      case 'high': return styles.riskHigh;
      case 'medium': return styles.riskMedium;
      case 'low': return styles.riskLow;
      default: return styles.riskUnknown;
    }
  };

  const getJsLevelColor = (level: string) => {
    switch (level) {
      case 'high': return styles.jsHigh;
      case 'medium': return styles.jsMedium;
      case 'low': return styles.jsLow;
      default: return styles.jsUnknown;
    }
  };

  return (
    <div className={styles.container}>
      <div className={styles.header} onClick={() => setIsExpanded(!isExpanded)}>
        <div className={styles.engineInfo}>
          <span className={styles.engineIcon}>{getEngineIcon(reason.selected_engine)}</span>
          <div className={styles.engineDetails}>
            <h3 className={styles.engineName}>
              {reason.selected_engine} <span className={styles.engineDesc}>({getEngineDescription(reason.selected_engine)})</span>
            </h3>
            <div className={styles.analysisMethod}>
              <span className={styles.methodBadge}>{reason.analysis_method}</span>
              <span className={`${styles.confidence} ${getConfidenceColor(reason.confidence)}`}>
                신뢰도: {Math.round(reason.confidence * 100)}%
              </span>
            </div>
          </div>
        </div>
        <button className={`${styles.expandButton} ${isExpanded ? styles.expanded : ''}`}>
          {isExpanded ? '▲' : '▼'}
        </button>
      </div>

      {isExpanded && (
        <div className={styles.content}>
          {/* 사이트 특성 */}
          <div className={styles.section}>
            <h4 className={styles.sectionTitle}>🔍 사이트 분석 결과</h4>
            <div className={styles.characteristics}>
              <div className={styles.characteristic}>
                <span className={styles.label}>사이트 유형:</span>
                <span className={styles.value}>{reason.site_characteristics.site_type}</span>
              </div>
              <div className={styles.characteristic}>
                <span className={styles.label}>JavaScript 복잡도:</span>
                <span className={`${styles.value} ${getJsLevelColor(reason.site_characteristics.javascript_level)}`}>
                  {reason.site_characteristics.javascript_level} ({reason.site_characteristics.javascript_score}/100)
                </span>
              </div>
              <div className={styles.characteristic}>
                <span className={styles.label}>봇 차단 위험도:</span>
                <span className={`${styles.value} ${getRiskColor(reason.site_characteristics.anti_bot_risk)}`}>
                  {reason.site_characteristics.anti_bot_risk}
                </span>
              </div>
              <div className={styles.characteristic}>
                <span className={styles.label}>JavaScript 실행 필요:</span>
                <span className={styles.value}>
                  {reason.site_characteristics.requires_js ? '✅ 예' : '❌ 아니오'}
                </span>
              </div>
            </div>
          </div>

          {/* 선택 이유 */}
          <div className={styles.section}>
            <h4 className={styles.sectionTitle}>🎯 엔진 선택 이유</h4>
            <ul className={styles.reasonsList}>
              {reason.selection_reasons.map((reasonText, index) => (
                <li key={index} className={styles.reason}>
                  {reasonText}
                </li>
              ))}
            </ul>
          </div>

          {/* 폴백 엔진 */}
          {reason.fallback_engines.length > 0 && (
            <div className={styles.section}>
              <h4 className={styles.sectionTitle}>🔄 폴백 엔진</h4>
              <div className={styles.fallbackEngines}>
                {reason.fallback_engines.map((engine, index) => (
                  <span key={index} className={styles.fallbackEngine}>
                    {getEngineIcon(engine)} {engine}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* 기술적 세부사항 */}
          <div className={styles.section}>
            <h4 className={styles.sectionTitle}>⚙️ 기술적 세부사항</h4>
            <div className={styles.technicalDetails}>
              <div className={styles.detail}>
                <span className={styles.label}>스크립트 개수:</span>
                <span className={styles.value}>{reason.technical_details.script_count}개</span>
              </div>
              <div className={styles.detail}>
                <span className={styles.label}>콘텐츠 비율:</span>
                <span className={styles.value}>{Math.round(reason.technical_details.content_ratio * 100)}%</span>
              </div>
              <div className={styles.detail}>
                <span className={styles.label}>시도한 엔진:</span>
                <span className={styles.value}>{reason.technical_details.success_on_attempt}번째 시도에서 성공</span>
              </div>
              {reason.technical_details.mcp_reasoning && (
                <div className={styles.detail}>
                  <span className={styles.label}>AI 분석 결론:</span>
                  <span className={styles.value}>{reason.technical_details.mcp_reasoning}</span>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default EngineSelectionInfo; 