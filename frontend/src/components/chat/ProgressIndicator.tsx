'use client';

import { ProgressIndicatorProps } from '@/types';
import styles from './ProgressIndicator.module.css';

const ProgressIndicator: React.FC<ProgressIndicatorProps> = ({
  progress,
  currentStep,
}) => {
  return (
    <div className={styles.container}>
      <div className={styles.stepInfo}>
        <span className={styles.stepText}>{currentStep}</span>
        <span className={styles.percentage}>{progress}%</span>
      </div>
      
      <div className={styles.progressBar}>
        <div 
          className={styles.progressFill}
          style={{ width: `${progress}%` }}
        />
      </div>

      <div className={styles.loadingDots}>
        <div className={styles.dot}></div>
        <div className={styles.dot}></div>
        <div className={styles.dot}></div>
      </div>
    </div>
  );
};

export default ProgressIndicator; 