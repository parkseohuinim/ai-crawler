// 고유한 ID 생성 유틸리티

let messageCounter = 0;

/**
 * 고유한 메시지 ID 생성
 * 시간 + 카운터 조합으로 중복 방지
 */
export function generateMessageId(): string {
  messageCounter += 1;
  return `msg_${Date.now()}_${messageCounter}`;
}

/**
 * 고유한 작업 ID 생성
 */
export function generateJobId(): string {
  return `job_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
}

/**
 * UUID v4 스타일 ID 생성 (간단 버전)
 */
export function generateUniqueId(): string {
  return 'xxxx-xxxx-4xxx-yxxx'.replace(/[xy]/g, function(c) {
    const r = Math.random() * 16 | 0;
    const v = c === 'x' ? r : (r & 0x3 | 0x8);
    return v.toString(16);
  });
} 