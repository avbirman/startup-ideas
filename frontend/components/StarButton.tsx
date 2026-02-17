'use client';

import { useState } from 'react';
import { api } from '@/lib/api';

interface StarButtonProps {
  problemId: number;
  isStarred: boolean;
  size?: 'sm' | 'md' | 'lg';
  onToggle?: (isStarred: boolean) => void;
}

export function StarButton({ problemId, isStarred: initialStarred, size = 'md', onToggle }: StarButtonProps) {
  const [starred, setStarred] = useState(initialStarred);
  const [loading, setLoading] = useState(false);

  const sizeClass = {
    sm: 'text-lg',
    md: 'text-xl',
    lg: 'text-2xl',
  }[size];

  const handleClick = async (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (loading) return;

    setLoading(true);
    try {
      const newValue = !starred;
      await api.toggleStar(problemId, newValue);
      setStarred(newValue);
      onToggle?.(newValue);
    } catch (err) {
      console.error('Failed to toggle star:', err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <button
      onClick={handleClick}
      disabled={loading}
      className={`${sizeClass} rounded-md transition-all hover:scale-110 ${loading ? 'opacity-50' : ''} ${starred ? 'text-amber-400' : 'text-[var(--muted)] hover:text-amber-300'}`}
      title={starred ? 'Убрать из избранного' : 'Добавить в избранное'}
    >
      {starred ? '\u2605' : '\u2606'}
    </button>
  );
}
