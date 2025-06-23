// URL 감지 및 추출 유틸리티

export interface DetectedUrl {
  url: string;
  isValid: boolean;
  domain: string;
}

export interface UrlDetectionResult {
  urls: DetectedUrl[];
  count: number;
  isMultiple: boolean;
  originalText: string;
  duplicateCount: number; // 중복 제거된 URL 개수
  originalCount: number; // 원본 URL 개수
}

/**
 * 텍스트에서 URL을 감지하고 추출합니다
 */
export function detectUrls(text: string): UrlDetectionResult {
  // 1. 완전한 URL 패턴 (http/https 포함)
  const completeUrlPattern = /https?:\/\/[^\s\n\r<>"{}|\\^`[\]]+/g;
  
  // 2. 프로토콜 없는 도메인 패턴 (예: shop.kt.com/path)
  const domainPattern = /(?:^|\s)([a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}(?:\/[^\s\n\r<>"{}|\\^`[\]]*)?/g;
  
  const completeMatches = text.match(completeUrlPattern) || [];
  const domainMatches = text.match(domainPattern) || [];
  
  // 프로토콜 없는 도메인들을 https://로 변환
  const normalizedDomainMatches = domainMatches.map(match => {
    const trimmed = match.trim();
    return trimmed.startsWith('http') ? trimmed : `https://${trimmed}`;
  });
  
  // 모든 URL 합치기
  const allUrls = [...completeMatches, ...normalizedDomainMatches];
  
  // URL 끝에서 구두점 제거 (쉼표, 마침표, 세미콜론 등)
  const cleanedUrls = allUrls.map(url => {
    return url.replace(/[.,;:!?]+$/, ''); // 끝에 있는 구두점들 제거
  });
  
  const originalCount = cleanedUrls.length; // 원본 개수
  const uniqueUrls = [...new Set(cleanedUrls)]; // 중복 제거
  const duplicateCount = originalCount - uniqueUrls.length; // 중복된 개수
  
  const detectedUrls: DetectedUrl[] = uniqueUrls.map(url => {
    let isValid = true;
    let domain = '';
    
    try {
      const urlObj = new URL(url);
      domain = urlObj.hostname;
      
      // 기본적인 유효성 검사
      if (!urlObj.protocol.startsWith('http')) {
        isValid = false;
      }
    } catch {
      isValid = false;
      domain = 'invalid';
    }
    
    return {
      url: url.trim(),
      isValid,
      domain
    };
  });
  
  return {
    urls: detectedUrls,
    count: detectedUrls.length,
    isMultiple: detectedUrls.length > 1,
    originalText: text,
    duplicateCount,
    originalCount
  };
}

/**
 * 유효한 URL만 필터링합니다
 */
export function getValidUrls(detection: UrlDetectionResult): string[] {
  return detection.urls
    .filter(item => item.isValid)
    .map(item => item.url);
}

/**
 * URL 감지 결과를 사용자 친화적인 메시지로 변환합니다
 */
export function getDetectionMessage(detection: UrlDetectionResult): string {
  const validCount = detection.urls.filter(u => u.isValid).length;
  const invalidCount = detection.count - validCount;
  
  if (detection.count === 0) {
    return "URL을 찾을 수 없습니다. 올바른 URL을 입력해주세요.";
  }
  
  if (detection.count === 1) {
    if (!detection.urls[0].isValid) {
      return "유효하지 않은 URL입니다.";
    }
    
    try {
      const urlObj = new URL(detection.urls[0].url);
      // 경로 + 쿼리 파라미터 포함하여 표시 (50자 제한)
      const pathWithQuery = `${urlObj.pathname}${urlObj.search}`;
      const displayPath = pathWithQuery.length > 50 ? 
        pathWithQuery.substring(0, 47) + '...' : 
        pathWithQuery;
      
      return `URL을 감지했습니다: ${urlObj.hostname}${displayPath || '/'}`;
    } catch {
      return `URL을 감지했습니다: ${detection.urls[0].domain}`;
    }
  }
  
  let message = `${validCount}개의 URL을 감지했습니다`;
  
  if (invalidCount > 0) {
    message += ` (${invalidCount}개는 유효하지 않음)`;
  }
  
  const domains = detection.urls
    .filter(u => u.isValid)
    .map(u => u.domain)
    .slice(0, 3); // 최대 3개까지만 표시
  
  if (domains.length > 0) {
    message += `\n• ${domains.join(', ')}`;
    if (validCount > 3) {
      message += ` 외 ${validCount - 3}개`;
    }
  }
  
  return message;
}

/**
 * 크롤링 타입을 결정합니다
 */
export function getCrawlingType(detection: UrlDetectionResult): 'single' | 'bulk' | 'invalid' {
  const validCount = detection.urls.filter(u => u.isValid).length;
  
  if (validCount === 0) return 'invalid';
  if (validCount === 1) return 'single';
  return 'bulk';
} 