'use client';

import { useEffect, useRef } from 'react';
import { MessageListProps } from '@/types';
import styles from './MessageList.module.css';

const MessageList: React.FC<MessageListProps> = ({ messages }) => {
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const formatTime = (timestamp: Date | string) => {
    const date = typeof timestamp === 'string' ? new Date(timestamp) : timestamp;
    return date.toLocaleTimeString('ko-KR', {
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const isUrl = (text: string) => {
    try {
      new URL(text);
      return true;
    } catch {
      return false;
    }
  };

  return (
    <div className={styles.container}>
      {messages.map((message) => (
        <div
          key={message.id}
          className={`${styles.message} ${
            message.type === 'user' ? styles.userMessage : styles.systemMessage
          } ${message.isError ? styles.errorMessage : ''}`}
        >
          <div className={styles.messageContent}>
            {message.type === 'user' && isUrl(message.content) ? (
              <div className={styles.urlMessage}>
                <span className={styles.urlIcon}>🔗</span>
                <span className={styles.urlText}>{message.content}</span>
                {message.metadata?.engine && (
                  <span className={styles.engineBadge}>{message.metadata.engine}</span>
                )}
              </div>
            ) : (
              <div className={styles.textContent}>
                {message.content}
                {message.metadata?.quality && (
                  <span className={styles.qualityBadge}>품질: {message.metadata.quality}/100</span>
                )}
              </div>
            )}
          </div>
          <div className={styles.timestamp}>
            {formatTime(message.timestamp)}
          </div>
        </div>
      ))}
      <div ref={messagesEndRef} />
    </div>
  );
};

export default MessageList; 