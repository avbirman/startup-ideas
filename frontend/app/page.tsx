'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { Sparkles, TrendingUp } from 'lucide-react';
import { api } from '@/lib/api';
import { StatsCard } from '@/components/StatsCard';
import { ProblemCard } from '@/components/ProblemCard';
import type { Stats, Problem } from '@/types';

export default function DashboardPage() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [recentProblems, setRecentProblems] = useState<Problem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadData() {
      try {
        setLoading(true);
        const [statsData, problemsData] = await Promise.all([
          api.getStats(),
          api.getProblems({ limit: 5, sort_by: 'date' }),
        ]);
        setStats(statsData);
        setRecentProblems(problemsData);
        setError(null);
      } catch (err) {
        console.error('Ошибка загрузки данных:', err);
        setError('Не удалось загрузить данные. Проверьте backend на http://localhost:8000');
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  if (loading) {
    return (
      <div className="page-shell flex items-center justify-center">
        <div className="app-card p-8 text-center">
          <div className="mx-auto h-10 w-10 animate-spin rounded-full border-2 border-[var(--border)] border-t-[var(--accent)]" />
          <p className="mt-3 text-sm text-[var(--muted)]">Загрузка дашборда...</p>
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
          <button
            onClick={() => window.location.reload()}
            className="btn-primary mt-5 rounded-xl px-4 py-2 text-sm font-semibold"
          >
            Повторить
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="page-shell">
      <main className="app-container space-y-8">
        <section className="app-card overflow-hidden p-6 sm:p-8">
          <div className="flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
            <div>
              <p className="inline-flex items-center gap-2 rounded-full bg-[var(--accent-soft)] px-3 py-1 text-xs font-semibold text-[var(--text)]">
                <Sparkles size={14} />
                AI Pipeline Monitor
              </p>
              <h1 className="title-display mt-4 text-3xl font-bold text-[var(--text)] sm:text-4xl">
                Коллектор Startup Идей
              </h1>
              <p className="mt-3 max-w-2xl text-sm text-[var(--muted)] sm:text-base">
                Находите реальные проблемы пользователей, анализируйте рыночный потенциал и отбирайте идеи с высоким шансом запуска.
              </p>
            </div>
            <div className="flex flex-wrap gap-2">
              <Link href="/problems" className="btn-primary rounded-xl px-4 py-2 text-sm font-semibold">Все проблемы</Link>
              <Link href="/problems?is_starred=true" className="btn-secondary rounded-xl px-4 py-2 text-sm font-semibold">
                Избранные ({stats?.starred_count || 0})
              </Link>
              <Link href="/scraping" className="btn-secondary rounded-xl px-4 py-2 text-sm font-semibold">Скрейпинг</Link>
            </div>
          </div>
        </section>

        <section className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-4">
          <StatsCard label="Всего проблем" value={stats?.totals.problems || 0} sublabel={`${stats?.totals.ideas || 0} startup идей`} icon="📝" />
          <StatsCard label="Дискуссий" value={stats?.totals.discussions || 0} sublabel={`${stats?.today.discussions || 0} сегодня`} icon="📊" />
          <StatsCard
            label="Средний Score"
            value={stats?.average_scores.overall?.toFixed(1) || '0.0'}
            sublabel="Общая уверенность"
            icon="⭐"
            trend={(stats?.average_scores.overall || 0) >= 70 ? 'up' : 'neutral'}
          />
          <StatsCard label="Избранные" value={stats?.starred_count || 0} sublabel="Точки фокуса" icon="★" />
        </section>

        {stats?.card_statuses && (
          <section className="app-card p-6">
            <h2 className="title-display text-xl font-semibold">Воронка статусов</h2>
            <div className="mt-4 grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-6">
              {[
                { key: 'new', label: 'Новые' },
                { key: 'viewed', label: 'Просмотрены' },
                { key: 'in_review', label: 'На ревью' },
                { key: 'verified', label: 'Проверены' },
                { key: 'archived', label: 'Архив' },
                { key: 'rejected', label: 'Отклонены' },
              ].map((s) => (
                <div key={s.key} className="rounded-xl border border-[var(--border)] bg-[var(--card-2)] p-3 text-center">
                  <p className="text-2xl font-bold text-[var(--text)]">
                    {stats.card_statuses[s.key as keyof typeof stats.card_statuses] || 0}
                  </p>
                  <p className="text-xs text-[var(--muted)]">{s.label}</p>
                </div>
              ))}
            </div>
          </section>
        )}

        <section>
          <div className="mb-4 flex items-center justify-between">
            <h2 className="title-display flex items-center gap-2 text-2xl font-semibold">
              <TrendingUp size={22} />
              Последние проблемы
            </h2>
            <Link href="/problems" className="text-sm font-semibold text-[var(--accent)]">Смотреть все</Link>
          </div>

          {recentProblems.length === 0 ? (
            <div className="app-card p-10 text-center">
              <h3 className="title-display text-xl font-semibold">Проблем пока нет</h3>
              <p className="mt-2 text-sm text-[var(--muted)]">Запустите скрейпер и начните формировать пул идей.</p>
              <button
                onClick={() => api.triggerScrape({ source: 'hackernews', limit: 10, analyze: true })}
                className="btn-primary mt-5 rounded-xl px-5 py-2.5 text-sm font-semibold"
              >
                Запустить скрейпинг
              </button>
            </div>
          ) : (
            <div className="grid grid-cols-1 gap-4">
              {recentProblems.map((problem) => (
                <ProblemCard key={problem.id} problem={problem} />
              ))}
            </div>
          )}
        </section>
      </main>
    </div>
  );
}
