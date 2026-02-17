'use client';

import type { CardStatus, ProblemFilters } from '@/types';

interface FilterPanelProps {
  filters: ProblemFilters;
  onChange: (filters: ProblemFilters) => void;
}

const STATUS_OPTIONS: { value: string; label: string }[] = [
  { value: '', label: 'Все статусы' },
  { value: 'new', label: 'Новые' },
  { value: 'viewed', label: 'Просмотренные' },
  { value: 'in_review', label: 'На рассмотрении' },
  { value: 'verified', label: 'Проверенные' },
];

const SORT_OPTIONS: { value: string; label: string }[] = [
  { value: 'score', label: 'По баллам' },
  { value: 'date', label: 'По дате' },
  { value: 'severity', label: 'По критичности' },
  { value: 'engagement', label: 'По вовлеченности' },
];

const SCORE_OPTIONS: { value: number; label: string }[] = [
  { value: 0, label: 'Все' },
  { value: 50, label: '50+' },
  { value: 60, label: '60+' },
  { value: 70, label: '70+' },
  { value: 80, label: '80+' },
];

const selectClass = 'input-ui text-sm';

export function FilterPanel({ filters, onChange }: FilterPanelProps) {
  const update = (patch: Partial<ProblemFilters>) => {
    onChange({ ...filters, ...patch });
  };

  return (
    <div className="app-card mb-6 p-4">
      <div className="flex flex-wrap gap-4 items-center">
        {/* Sort */}
        <div className="flex items-center gap-2">
          <label className="text-sm font-medium text-[var(--muted)]">Сортировка:</label>
          <select
            value={filters.sort_by || 'score'}
            onChange={(e) => update({ sort_by: e.target.value as any })}
            className={selectClass}
          >
            {SORT_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>{o.label}</option>
            ))}
          </select>
        </div>

        {/* Min Score */}
        <div className="flex items-center gap-2">
          <label className="text-sm font-medium text-[var(--muted)]">Мин. балл:</label>
          <select
            value={filters.min_score || 0}
            onChange={(e) => update({ min_score: Number(e.target.value) || undefined })}
            className={selectClass}
          >
            {SCORE_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>{o.label}</option>
            ))}
          </select>
        </div>

        {/* Status */}
        <div className="flex items-center gap-2">
          <label className="text-sm font-medium text-[var(--muted)]">Статус:</label>
          <select
            value={filters.status || ''}
            onChange={(e) => update({ status: (e.target.value || undefined) as CardStatus | undefined })}
            className={selectClass}
          >
            {STATUS_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>{o.label}</option>
            ))}
          </select>
        </div>

        {/* Starred */}
        <label className="flex cursor-pointer items-center gap-2 text-sm font-medium text-[var(--muted)]">
          <input
            type="checkbox"
            checked={filters.is_starred === true}
            onChange={(e) => update({ is_starred: e.target.checked || undefined })}
            className="rounded border-[var(--border)]"
          />
          Только избранные
        </label>

        {/* Analysis Tier */}
        <div className="flex items-center gap-2">
          <label className="text-sm font-medium text-[var(--muted)]">Анализ:</label>
          <select
            value={filters.analysis_tier || ''}
            onChange={(e) => update({ analysis_tier: (e.target.value || undefined) as 'basic' | 'deep' | undefined })}
            className={selectClass}
          >
            <option value="">Все</option>
            <option value="basic">Basic</option>
            <option value="deep">Deep</option>
          </select>
        </div>

        {/* Audience Type */}
        <div className="flex items-center gap-2">
          <label className="text-sm font-medium text-[var(--muted)]">Тип кейса:</label>
          <select
            value={filters.audience_type || ''}
            onChange={(e) =>
              update({
                audience_type: (e.target.value || undefined) as
                  | 'consumers'
                  | 'entrepreneurs'
                  | 'mixed'
                  | 'unknown'
                  | undefined,
              })
            }
            className={selectClass}
          >
            <option value="">Все</option>
            <option value="consumers">Для простых людей (B2C)</option>
            <option value="entrepreneurs">Для предпринимателей</option>
            <option value="mixed">Смешанный</option>
            <option value="unknown">Не определён</option>
          </select>
        </div>
      </div>
    </div>
  );
}
