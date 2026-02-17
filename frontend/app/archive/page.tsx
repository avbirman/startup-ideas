'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { ArchiveRestore } from 'lucide-react';
import { api } from '@/lib/api';
import { StatusBadge } from '@/components/StatusBadge';
import type { Problem } from '@/types';

export default function ArchivePage() {
  const [problems, setProblems] = useState<Problem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      try {
        setLoading(true);
        const data = await api.getArchivedProblems({ limit: 100 });
        setProblems(data);
        setError(null);
      } catch (err) {
        console.error('Failed to load archive:', err);
        setError('Не удалось загрузить архив');
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  const handleRestore = async (problemId: number) => {
    try {
      await api.updateCardStatus(problemId, 'viewed');
      setProblems((prev) => prev.filter((p) => p.id !== problemId));
    } catch (err) {
      console.error('Failed to restore:', err);
    }
  };

  if (loading) {
    return (
      <div className="page-shell flex items-center justify-center">
        <div className="app-card p-8 text-center">
          <div className="mx-auto h-10 w-10 animate-spin rounded-full border-2 border-[var(--border)] border-t-[var(--accent)]" />
          <p className="mt-3 text-sm text-[var(--muted)]">Загрузка архива...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="page-shell flex items-center justify-center px-4">
        <div className="app-card max-w-md p-8">
          <h2 className="title-display text-xl font-semibold text-[var(--danger)]">Ошибка</h2>
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
            <ArchiveRestore />
            Архив
          </h1>
          <p className="mt-2 text-sm text-[var(--muted)]">
            {problems.length} {problems.length === 1 ? 'карточка' : problems.length < 5 ? 'карточки' : 'карточек'} в архиве
          </p>
        </section>

        {problems.length === 0 ? (
          <div className="app-card p-10 text-center">
            <h3 className="title-display text-xl font-semibold">Архив пуст</h3>
            <p className="mt-2 text-sm text-[var(--muted)]">Архивированные и отклонённые карточки появятся здесь.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-4">
            {problems.map((problem) => (
              <div key={problem.id} className="app-card p-5 transition hover:-translate-y-0.5 hover:shadow-xl">
                <div className="flex flex-col items-start justify-between gap-4 sm:flex-row">
                  <div className="flex-1">
                    <div className="mb-2 flex items-center gap-2">
                      <StatusBadge status={problem.card_status} />
                      {problem.overall_score !== null && (
                        <span className="rounded-full bg-[var(--card-2)] px-2 py-0.5 text-xs text-[var(--muted)]">
                          {problem.overall_score}/100
                        </span>
                      )}
                    </div>
                    <Link href={`/problems/${problem.id}`} className="title-display text-lg font-semibold hover:text-[var(--accent)]">
                      {problem.problem_statement}
                    </Link>
                    <p className="mt-2 text-sm text-[var(--muted)]">
                      {problem.discussion.source_name} • ↑ {problem.discussion.upvotes} • 💡 {problem.ideas_count} идей
                    </p>
                  </div>
                  <button
                    onClick={() => handleRestore(problem.id)}
                    className="btn-primary rounded-xl px-4 py-2 text-sm font-semibold"
                  >
                    Восстановить
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
