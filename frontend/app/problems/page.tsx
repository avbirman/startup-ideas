'use client';

import { useEffect, useState, useCallback } from 'react';
import { SearchCheck } from 'lucide-react';
import { api } from '@/lib/api';
import { ProblemCard } from '@/components/ProblemCard';
import { FilterPanel } from '@/components/FilterPanel';
import type { AudienceType, Problem, ProblemFilters } from '@/types';

export default function ProblemsPage() {
  const [problems, setProblems] = useState<Problem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filters, setFilters] = useState<ProblemFilters>({
    sort_by: 'score',
    limit: 50,
  });

  const loadProblems = useCallback(async () => {
    try {
      setLoading(true);
      const data = await api.getProblems({
        ...filters,
        min_score: filters.min_score && filters.min_score > 0 ? filters.min_score : undefined,
      });
      setProblems(data);
      setError(null);
    } catch (err) {
      console.error('Failed to load problems:', err);
      setError('Не удалось загрузить проблемы. Убедитесь, что backend запущен.');
    } finally {
      setLoading(false);
    }
  }, [filters]);

  useEffect(() => {
    loadProblems();
  }, [loadProblems]);

  const handleStarToggle = (problemId: number, isStarred: boolean) => {
    setProblems((prev) =>
      prev.map((p) => (p.id === problemId ? { ...p, is_starred: isStarred } : p))
    );
  };

  const setAudienceTab = (audienceType?: AudienceType) => {
    setFilters((prev) => ({
      ...prev,
      audience_type: audienceType,
    }));
  };

  if (loading) {
    return (
      <div className="page-shell flex items-center justify-center">
        <div className="app-card p-8 text-center">
          <div className="mx-auto h-10 w-10 animate-spin rounded-full border-2 border-[var(--border)] border-t-[var(--accent)]" />
          <p className="mt-3 text-sm text-[var(--muted)]">Загрузка проблем...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="page-shell flex items-center justify-center px-4">
        <div className="app-card max-w-md p-8">
          <h2 className="title-display text-xl font-semibold text-[var(--danger)]">Ошибка подключения</h2>
          <p className="mt-2 text-sm text-[var(--muted)]">{error}</p>
          <button onClick={() => window.location.reload()} className="btn-primary mt-5 rounded-xl px-4 py-2 text-sm font-semibold">
            Повторить
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="page-shell">
      <main className="app-container space-y-6">
        <section className="app-card p-6">
          <h1 className="title-display flex items-center gap-2 text-3xl font-bold">
            <SearchCheck />
            Все проблемы
          </h1>
          <p className="mt-2 text-sm text-[var(--muted)]">
            {problems.length} {problems.length === 1 ? 'проблема' : problems.length < 5 ? 'проблемы' : 'проблем'} по текущим фильтрам
          </p>
          <div className="mt-4 flex flex-wrap gap-2">
            <button
              onClick={() => setAudienceTab(undefined)}
              className={`rounded-xl px-3 py-1.5 text-sm font-semibold transition ${
                !filters.audience_type
                  ? 'btn-primary'
                  : 'btn-secondary'
              }`}
            >
              Все
            </button>
            <button
              onClick={() => setAudienceTab('consumers')}
              className={`rounded-xl px-3 py-1.5 text-sm font-semibold transition ${
                filters.audience_type === 'consumers'
                  ? 'btn-primary'
                  : 'btn-secondary'
              }`}
            >
              B2C: простые люди
            </button>
            <button
              onClick={() => setAudienceTab('entrepreneurs')}
              className={`rounded-xl px-3 py-1.5 text-sm font-semibold transition ${
                filters.audience_type === 'entrepreneurs'
                  ? 'btn-primary'
                  : 'btn-secondary'
              }`}
            >
              Для предпринимателей
            </button>
          </div>
        </section>

        <FilterPanel filters={filters} onChange={setFilters} />

        {problems.length === 0 ? (
          <div className="app-card p-10 text-center">
            <h3 className="title-display text-xl font-semibold">Проблем не найдено</h3>
            <p className="mt-2 text-sm text-[var(--muted)]">Попробуйте изменить фильтры.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-4">
            {problems.map((problem) => (
              <ProblemCard key={problem.id} problem={problem} onStarToggle={handleStarToggle} />
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
