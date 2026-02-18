'use client';

import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { ArrowLeft } from 'lucide-react';
import { api } from '@/lib/api';
import { StatusBadge } from '@/components/StatusBadge';
import { StarButton } from '@/components/StarButton';
import { TagInput } from '@/components/TagInput';
import { NotesEditor } from '@/components/NotesEditor';
import type { ProblemDetail, CardStatus } from '@/types';

export default function ProblemDetailPage() {
  const params = useParams();
  const router = useRouter();
  const problemId = parseInt(params.id as string);

  const [problem, setProblem] = useState<ProblemDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [statusLoading, setStatusLoading] = useState(false);

  useEffect(() => {
    async function loadProblem() {
      try {
        setLoading(true);
        const data = await api.getProblem(problemId);
        // Auto-mark as viewed if still new
        if (data.card_status === 'new') {
          api.updateCardStatus(problemId, 'viewed').catch(() => {});
          data.card_status = 'viewed';
        }
        setProblem(data);
        setError(null);
      } catch (err) {
        console.error('Failed to load problem:', err);
        setError('Не удалось загрузить детали проблемы');
      } finally {
        setLoading(false);
      }
    }
    if (problemId) loadProblem();
  }, [problemId]);

  const handleStatusChange = async (status: CardStatus) => {
    if (!problem || statusLoading) return;
    setStatusLoading(true);
    try {
      await api.updateCardStatus(problemId, status);
      setProblem({ ...problem, card_status: status });
    } catch (err) {
      console.error('Failed to update status:', err);
    } finally {
      setStatusLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="page-shell flex items-center justify-center">
        <div className="app-card p-8 text-center">
          <div className="mx-auto h-10 w-10 animate-spin rounded-full border-2 border-[var(--border)] border-t-[var(--accent)]" />
          <p className="mt-3 text-sm text-[var(--muted)]">Загрузка...</p>
        </div>
      </div>
    );
  }

  if (error || !problem) {
    return (
      <div className="page-shell flex items-center justify-center px-4">
        <div className="app-card max-w-md p-8">
          <h2 className="title-display text-xl font-semibold text-[var(--danger)]">Ошибка</h2>
          <p className="mt-2 text-sm text-[var(--muted)]">{error || 'Проблема не найдена'}</p>
          <button onClick={() => router.push('/')} className="btn-primary mt-5 rounded-xl px-4 py-2 text-sm font-semibold">
            На главную
          </button>
        </div>
      </div>
    );
  }

  const statusActions: { status: CardStatus; label: string; className: string }[] = [
    { status: 'in_review', label: 'На рассмотрение', className: 'bg-amber-500 text-white' },
    { status: 'verified', label: 'Верифицировать', className: 'bg-emerald-600 text-white' },
    { status: 'archived', label: 'В архив', className: 'bg-slate-500 text-white' },
    { status: 'rejected', label: 'Отклонить', className: 'bg-rose-500 text-white' },
  ];

  return (
    <div className="page-shell">
      <main className="app-container space-y-6">
        <section className="app-card p-6">
          <button onClick={() => router.back()} className="mb-4 inline-flex items-center gap-1 text-sm font-semibold text-[var(--accent)]">
            <ArrowLeft size={16} />
            К списку проблем
          </button>
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <h1 className="title-display text-3xl font-bold">Анализ проблемы</h1>
              <div className="mt-2"><StatusBadge status={problem.card_status} size="md" /></div>
            </div>
            <StarButton problemId={problemId} isStarred={problem.is_starred} size="lg" />
          </div>
        </section>

        <section className="app-card p-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex flex-wrap items-center gap-2">
              {statusActions.filter((a) => a.status !== problem.card_status).map((action) => (
                <button
                  key={action.status}
                  onClick={() => handleStatusChange(action.status)}
                  disabled={statusLoading}
                  className={`rounded-lg px-3 py-1.5 text-sm font-semibold transition disabled:opacity-60 ${action.className}`}
                >
                  {action.label}
                </button>
              ))}
            </div>
            <div className="text-sm text-[var(--muted)]">
              Просмотров: {problem.view_count}
              {problem.first_viewed_at && (
                <span className="ml-2">• {new Date(problem.first_viewed_at).toLocaleDateString('ru-RU')}</span>
              )}
            </div>
          </div>
        </section>

        <section className="app-card p-6">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
            <div className="max-w-3xl">
              <h2 className="title-display text-2xl font-semibold">{problem.problem_statement}</h2>
              <p className="mt-2 text-sm text-[var(--muted)]">Целевая аудитория: {problem.target_audience || 'Не указано'}</p>
            </div>
            {problem.overall_score !== null && (
              <div className="rounded-2xl bg-[var(--accent-soft)] px-5 py-3 text-center">
                <p className="title-display text-4xl font-bold">{problem.overall_score}</p>
                <p className="text-xs text-[var(--muted)]">Общий балл</p>
              </div>
            )}
          </div>
        </section>

        <section className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          <div className="app-card p-6">
            <h3 className="title-display mb-4 text-xl font-semibold">Детали проблемы</h3>
            <div className="space-y-3 text-sm">
              <p><span className="font-semibold">Критичность:</span> {problem.severity || 'Не указано'}/10</p>
              {problem.current_solutions && <p><span className="font-semibold">Текущие решения:</span> {problem.current_solutions}</p>}
              {problem.why_they_fail && <p><span className="font-semibold">Почему не работают:</span> {problem.why_they_fail}</p>}
            </div>
          </div>

          {problem.marketing_analysis && (
            <div className="app-card p-6">
              <h3 className="title-display mb-4 text-xl font-semibold">Анализ рынка</h3>
              <div className="space-y-3 text-sm">
                {problem.marketing_analysis.tam && <p><span className="font-semibold">TAM:</span> {problem.marketing_analysis.tam}</p>}
                {problem.marketing_analysis.sam && <p><span className="font-semibold">SAM:</span> {problem.marketing_analysis.sam}</p>}
                {problem.marketing_analysis.som && <p><span className="font-semibold">SOM:</span> {problem.marketing_analysis.som}</p>}
                {problem.marketing_analysis.positioning && <p><span className="font-semibold">Позиционирование:</span> {problem.marketing_analysis.positioning}</p>}
                {problem.marketing_analysis.competitive_moat && <p><span className="font-semibold">Преимущество:</span> {problem.marketing_analysis.competitive_moat}</p>}
              </div>
            </div>
          )}
        </section>

        {problem.startup_ideas && problem.startup_ideas.length > 0 && (
          <section className="app-card p-6">
            <h3 className="title-display mb-4 text-xl font-semibold">Идеи стартапов ({problem.startup_ideas.length})</h3>
            <div className="space-y-3">
              {problem.startup_ideas.map((idea, index) => (
                <div key={idea.id} className="rounded-xl border border-[var(--border)] bg-[var(--card-2)] p-4">
                  <h4 className="font-semibold">{index + 1}. {idea.idea_title}</h4>
                  <p className="mt-2 text-sm text-[var(--muted)]">{idea.description}</p>
                  {idea.approach && <p className="mt-2 text-xs"><span className="font-semibold">Подход:</span> {idea.approach}</p>}
                  {idea.value_proposition && <p className="mt-1 text-xs"><span className="font-semibold">Ценность:</span> {idea.value_proposition}</p>}
                  {idea.core_features && idea.core_features.length > 0 && (
                    <div className="mt-2 flex flex-wrap gap-1">
                      {idea.core_features.map((f) => (
                        <span key={f} className="rounded-full bg-[var(--card)] px-2 py-0.5 text-xs text-[var(--muted)]">{f}</span>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </section>
        )}

        <section className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          <div className="app-card p-6">
            <h3 className="title-display mb-4 text-xl font-semibold">Заметки</h3>
            <NotesEditor problemId={problemId} notes={problem.user_notes} />
          </div>
          <div className="app-card p-6">
            <h3 className="title-display mb-4 text-xl font-semibold">Теги</h3>
            <TagInput problemId={problemId} tags={problem.user_tags || []} />
          </div>
        </section>

        {problem.discussion && (
          <section className="app-card p-6">
            <h3 className="title-display mb-4 text-xl font-semibold">Исходная дискуссия</h3>
            <div className="space-y-3 text-sm">
              <p><span className="font-semibold">Название:</span> {problem.discussion.title}</p>
              <p>
                <span className="font-semibold">Источник:</span>{' '}
                <a href={problem.discussion.url} target="_blank" rel="noopener noreferrer" className="font-semibold text-[var(--accent)]">
                  {problem.discussion.source_name} — открыть оригинал
                </a>
              </p>
              <p><span className="font-semibold">Вовлечённость:</span> {problem.discussion.upvotes} лайков, {problem.discussion.comments_count} комментариев</p>
            </div>
          </section>
        )}
      </main>
    </div>
  );
}
