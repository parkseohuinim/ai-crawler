'use client';

import { useState } from 'react';
import { ChatInputProps } from '@/types';
import styles from './ChatInput.module.css';

const ChatInput: React.FC<ChatInputProps> = ({ onSubmit, disabled = false }) => {
  const [inputValue, setInputValue] = useState('');

  const detectInputType = (input: string) => {
    const trimmed = input.trim();
    if (!trimmed) return 'empty';
    
    if (trimmed.match(/^https?:\/\//)) return 'url';
    if (trimmed.includes('http://') || trimmed.includes('https://')) return 'mixed';
    
    if (trimmed.includes('추출') || trimmed.includes('크롤링') || trimmed.includes('가져와')) return 'natural';
    if (trimmed.includes('찾아') || trimmed.includes('검색')) return 'search';
    
    return 'text';
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputValue.trim() || disabled) return;

    const input = inputValue.trim();
    onSubmit(input);
    setInputValue('');
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  const getHintMessage = () => {
    const type = detectInputType(inputValue);
    switch (type) {
      case 'url':
        return '🔗 URL 크롤링 모드';
      case 'mixed':
        return '📋 멀티 URL 크롤링 모드';
      case 'natural':
        return '🧠 선택적 추출 모드';
      case 'search':
        return '🔍 검색 모드 (준비 중)';
      case 'text':
        return '💬 자연어 입력 감지됨';
      default:
        return '';
    }
  };

  return (
    <div className={styles.container}>
      <form onSubmit={handleSubmit} className={styles.form}>
        <div className={styles.inputContainer}>
          <input
            type="text"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="URL 또는 자연어로 크롤링 요청하세요... (예: https://example.com 또는 '네이버 뉴스 제목 추출해줘')"
            className={styles.input}
            disabled={disabled}
          />
          <button 
            type="submit" 
            className={styles.submitButton}
            disabled={disabled || !inputValue.trim()}
          >
            {disabled ? (
              <div className={styles.spinner}></div>
            ) : (
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
                <path 
                  d="M22 2L11 13M22 2L15 22L11 13M22 2L2 9L11 13" 
                  stroke="currentColor" 
                  strokeWidth="2" 
                  strokeLinecap="round" 
                  strokeLinejoin="round"
                />
              </svg>
            )}
          </button>
        </div>
        {inputValue && getHintMessage() && (
          <div className={styles.hintMessage}>
            {getHintMessage()}
          </div>
        )}
      </form>
    </div>
  );
};

export default ChatInput; 