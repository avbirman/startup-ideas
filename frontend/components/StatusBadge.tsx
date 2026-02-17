'use client';

import type { CardStatus } from '@/types';

const STATUS_CONFIG: Record<CardStatus, { label: string; className: string }> = {
  new: { label: 'Новая', className: 'bg-cyan-500/20 text-cyan-700 dark:text-cyan-300' },
  viewed: { label: 'Просмотрена', className: 'bg-slate-500/20 text-slate-700 dark:text-slate-300' },
  in_review: { label: 'На рассмотрении', className: 'bg-amber-500/20 text-amber-700 dark:text-amber-300' },
  verified: { label: 'Проверена', className: 'bg-emerald-500/20 text-emerald-700 dark:text-emerald-300' },
  archived: { label: 'В архиве', className: 'bg-slate-600/20 text-slate-700 dark:text-slate-300' },
  rejected: { label: 'Отклонена', className: 'bg-rose-500/20 text-rose-700 dark:text-rose-300' },
};

interface StatusBadgeProps {
  status: CardStatus;
  size?: 'sm' | 'md';
}

export function StatusBadge({ status, size = 'sm' }: StatusBadgeProps) {
  const config = STATUS_CONFIG[status] || STATUS_CONFIG.new;
  const sizeClass = size === 'md' ? 'px-3 py-1 text-sm' : 'px-2 py-0.5 text-xs';

  return (
    <span className={`inline-flex items-center font-medium rounded-full ${sizeClass} ${config.className}`}>
      {config.label}
    </span>
  );
}
