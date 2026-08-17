import type { ButtonHTMLAttributes } from 'react';
import styles from './NeonButton.module.css';

interface NeonButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'danger' | 'success';
}

export function NeonButton({ children, variant = 'primary', className = '', ...props }: NeonButtonProps) {
  return (
    <button className={`${styles.neonButton} ${styles[variant]} ${className}`} {...props}>
      {children}
    </button>
  );
}
