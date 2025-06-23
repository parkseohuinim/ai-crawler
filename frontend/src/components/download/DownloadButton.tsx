'use client';

import { useState } from 'react';
import { DownloadButtonProps } from '@/types';
import styles from './DownloadButton.module.css';

const DownloadButton: React.FC<DownloadButtonProps> = ({ onDownload }) => {
  const [isDownloading, setIsDownloading] = useState(false);

  const handleDownload = async () => {
    setIsDownloading(true);
    
    try {
      onDownload();
      
      // Show success feedback
      setTimeout(() => setIsDownloading(false), 1000);
    } catch (error) {
      console.error('Download failed:', error);
      setIsDownloading(false);
    }
  };

  return (
    <button 
      className={styles.downloadButton}
      onClick={handleDownload}
      disabled={isDownloading}
    >
      {isDownloading ? (
        <>
          <div className={styles.spinner}></div>
          다운로드 중...
        </>
      ) : (
        <>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
            <path 
              d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M7 10l5 5 5-5M12 15V3" 
              stroke="currentColor" 
              strokeWidth="2" 
              strokeLinecap="round" 
              strokeLinejoin="round"
            />
          </svg>
          JSON 다운로드
        </>
      )}
    </button>
  );
};

export default DownloadButton; 