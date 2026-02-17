'use client';

import { useEffect, useState, useCallback } from 'react';
import { Bot, CalendarClock, History, Radar } from 'lucide-react';
import { api } from '@/lib/api';
import type { ScrapeSchedule, ScrapeLogEntry } from '@/types';

export default function ScrapingPage() {
  const [scrapeSource, setScrapeSource] = useState<'reddit' | 'hackernews' | 'youtube' | 'medium' | 'all'>('all');
  const [scrapeLimit, setScrapeLimit] = useState(10);
  const [scrapeAnalyze, setScrapeAnalyze] = useState(true);
  const [scrapeRunning, setScrapeRunning] = useState(false);
  const [scrapeMessage, setScrapeMessage] = useState<string | null>(null);

  const [schedule, setSchedule] = useState<ScrapeSchedule | null>(null);
  const [scheduleLoading, setScheduleLoading] = useState(true);
  const [schedSource, setSchedSource] = useState<'reddit' | 'hackernews' | 'youtube' | 'medium' | 'all'>('all');
  const [schedInterval, setSchedInterval] = useState(6);
  const [schedLimit, setSchedLimit] = useState(10);
  const [schedAnalyze, setSchedAnalyze] = useState(true);
  const [schedSaving, setSchedSaving] = useState(false);

  const [history, setHistory] = useState<ScrapeLogEntry[]>([]);
  const [historyLoading, setHistoryLoading] = useState(true);
  const [sources, setSources] = useState<Array<{ name: string; type: string; is_active: boolean; last_scraped: string | null }>>([]);

  useEffect(() => {
    api.getSchedule().then((data) => {
      if (data.enabled) {
        setSchedule(data);
        setSchedSource(data.source);
        setSchedInterval(data.interval_hours);
        setSchedLimit(data.limit);
        setSchedAnalyze(data.analyze);
      }
      setScheduleLoading(false);
    }).catch(() => setScheduleLoading(false));
  }, []);

  const loadHistory = useCallback(() => {
    api.getScrapeHistory(20).then(setHistory).catch(() => {}).finally(() => setHistoryLoading(false));
  }, []);

  useEffect(() => {
    loadHistory();
    const interval = setInterval(loadHistory, 30000);
    return () => clearInterval(interval);
  }, [loadHistory]);

  useEffect(() => {
    api.getSourcesStatus().then((data) => setSources(data.sources)).catch(() => {});
  }, []);

  const handleManualScrape = async () => {
    setScrapeRunning(true);
    setScrapeMessage(null);
    try {
      const result = await api.triggerScrape({
        source: scrapeSource,
        limit: scrapeLimit,
        analyze: scrapeAnalyze,
      });
      setScrapeMessage(result.message || 'Скрейпинг запущен');
      setTimeout(loadHistory, 2000);
    } catch {
      setScrapeMessage('Ошибка запуска скрейпинга');
    } finally {
      setScrapeRunning(false);
    }
  };

  const handleSaveSchedule = async () => {
    setSchedSaving(true);
    try {
      const result = await api.setSchedule({
        interval_hours: schedInterval,
        source: schedSource,
        limit: schedLimit,
        analyze: schedAnalyze,
      });
      setSchedule(result);
    } finally {
      setSchedSaving(false);
    }
  };

  const handleDeleteSchedule = async () => {
    setSchedSaving(true);
    try {
      await api.deleteSchedule();
      setSchedule(null);
    } finally {
      setSchedSaving(false);
    }
  };

  const formatDate = (iso: string | null) => {
    if (!iso) return '—';
    return new Date(iso).toLocaleString('ru-RU', {
      day: '2-digit', month: '2-digit', year: 'numeric',
      hour: '2-digit', minute: '2-digit',
    });
  };

  const sourceLabel = (s: string) => {
    if (s === 'reddit') return 'Reddit';
    if (s === 'hackernews') return 'Hacker News';
    if (s === 'all') return 'Все';
    return s;
  };

  const statusBadge = (status: string) => {
    const styles: Record<string, string> = {
      running: 'bg-cyan-500/20 text-cyan-600 dark:text-cyan-300',
      completed: 'bg-emerald-500/20 text-emerald-600 dark:text-emerald-300',
      failed: 'bg-rose-500/20 text-rose-600 dark:text-rose-300',
    };
    const labels: Record<string, string> = {
      running: 'Выполняется',
      completed: 'Завершено',
      failed: 'Ошибка',
    };
    return (
      <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${styles[status] || 'bg-[var(--card-2)] text-[var(--muted)]'}`}>
        {labels[status] || status}
      </span>
    );
  };

  return (
    <div className="page-shell">
      <main className="app-container space-y-6">
        <section className="app-card p-6">
          <h1 className="title-display flex items-center gap-2 text-3xl font-bold">
            <Radar />
            Скрейпинг
          </h1>
          <p className="mt-2 text-sm text-[var(--muted)]">Ручной запуск, расписание и история сборов.</p>
        </section>

        <section className="app-card p-6">
          <h2 className="title-display mb-4 flex items-center gap-2 text-xl font-semibold">
            <Bot size={20} />
            Ручной запуск
          </h2>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
            <select value={scrapeSource} onChange={(e) => setScrapeSource(e.target.value as any)} className="input-ui text-sm">
              <option value="all">Все источники</option>
              <option value="reddit">Reddit</option>
              <option value="hackernews">Hacker News</option>
              <option value="youtube">YouTube</option>
              <option value="medium">Medium</option>
            </select>
            <input
              type="number"
              value={scrapeLimit}
              onChange={(e) => setScrapeLimit(Math.max(1, parseInt(e.target.value) || 1))}
              min={1}
              max={100}
              className="input-ui text-sm"
            />
            <label className="flex items-center gap-2 rounded-xl border border-[var(--border)] bg-[var(--card-2)] px-3 py-2 text-sm">
              <input type="checkbox" checked={scrapeAnalyze} onChange={(e) => setScrapeAnalyze(e.target.checked)} />
              AI анализ
            </label>
          </div>
          <div className="mt-4 flex flex-wrap items-center gap-3">
            <button onClick={handleManualScrape} disabled={scrapeRunning} className="btn-primary rounded-xl px-5 py-2 text-sm font-semibold disabled:opacity-60">
              {scrapeRunning ? 'Запуск...' : 'Запустить'}
            </button>
            {scrapeMessage && <span className="text-sm text-[var(--muted)]">{scrapeMessage}</span>}
          </div>
        </section>

        <section className="app-card p-6">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="title-display flex items-center gap-2 text-xl font-semibold">
              <CalendarClock size={20} />
              Расписание
            </h2>
            {schedule?.enabled && <span className="rounded-full bg-emerald-500/20 px-3 py-1 text-xs font-semibold text-emerald-600 dark:text-emerald-300">Активно</span>}
          </div>

          {scheduleLoading ? (
            <p className="text-sm text-[var(--muted)]">Загрузка...</p>
          ) : (
            <>
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-4">
                <select value={schedInterval} onChange={(e) => setSchedInterval(parseInt(e.target.value))} className="input-ui text-sm">
                  <option value={1}>Каждый час</option>
                  <option value={3}>Каждые 3 часа</option>
                  <option value={6}>Каждые 6 часов</option>
                  <option value={12}>Каждые 12 часов</option>
                  <option value={24}>Раз в сутки</option>
                </select>
                <select value={schedSource} onChange={(e) => setSchedSource(e.target.value as any)} className="input-ui text-sm">
                  <option value="all">Все источники</option>
                  <option value="reddit">Reddit</option>
                  <option value="hackernews">Hacker News</option>
                  <option value="youtube">YouTube</option>
                  <option value="medium">Medium</option>
                </select>
                <input
                  type="number"
                  value={schedLimit}
                  onChange={(e) => setSchedLimit(Math.max(1, parseInt(e.target.value) || 1))}
                  min={1}
                  max={100}
                  className="input-ui text-sm"
                />
                <label className="flex items-center gap-2 rounded-xl border border-[var(--border)] bg-[var(--card-2)] px-3 py-2 text-sm">
                  <input type="checkbox" checked={schedAnalyze} onChange={(e) => setSchedAnalyze(e.target.checked)} />
                  AI анализ
                </label>
              </div>

              <div className="mt-4 flex flex-wrap gap-3">
                <button onClick={handleSaveSchedule} disabled={schedSaving} className="btn-primary rounded-xl px-4 py-2 text-sm font-semibold disabled:opacity-60">
                  {schedSaving ? 'Сохранение...' : schedule?.enabled ? 'Обновить' : 'Включить'}
                </button>
                {schedule?.enabled && (
                  <button onClick={handleDeleteSchedule} disabled={schedSaving} className="btn-danger rounded-xl px-4 py-2 text-sm font-semibold disabled:opacity-60">
                    Отключить
                  </button>
                )}
              </div>

              {schedule?.enabled && (
                <div className="mt-4 space-y-1 text-sm text-[var(--muted)]">
                  {schedule.next_run_at && <p>Следующий запуск: <span className="font-semibold text-[var(--text)]">{formatDate(schedule.next_run_at)}</span></p>}
                  {schedule.last_run_at && <p>Последний запуск: <span className="font-semibold text-[var(--text)]">{formatDate(schedule.last_run_at)}</span></p>}
                </div>
              )}
            </>
          )}
        </section>

        {sources.length > 0 && (
          <section className="app-card p-6">
            <h2 className="title-display mb-4 text-xl font-semibold">Источники</h2>
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {sources.map((src) => (
                <div key={src.name} className="rounded-xl border border-[var(--border)] bg-[var(--card-2)] p-4">
                  <div className="mb-1 flex items-center justify-between gap-2">
                    <span className="font-semibold">{src.name}</span>
                    <span className={`rounded-full px-2 py-0.5 text-xs ${src.is_active ? 'bg-emerald-500/20 text-emerald-600 dark:text-emerald-300' : 'bg-[var(--card)] text-[var(--muted)]'}`}>
                      {src.is_active ? 'Активен' : 'Неактивен'}
                    </span>
                  </div>
                  <p className="text-xs text-[var(--muted)]">Последний сбор: {formatDate(src.last_scraped)}</p>
                </div>
              ))}
            </div>
          </section>
        )}

        <section className="app-card p-6">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="title-display flex items-center gap-2 text-xl font-semibold">
              <History size={20} />
              История
            </h2>
            <button onClick={loadHistory} className="text-sm font-semibold text-[var(--accent)]">Обновить</button>
          </div>

          {historyLoading ? (
            <p className="text-sm text-[var(--muted)]">Загрузка...</p>
          ) : history.length === 0 ? (
            <p className="rounded-xl border border-[var(--border)] bg-[var(--card-2)] p-6 text-sm text-[var(--muted)]">Нет записей.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-[var(--border)] text-left text-[var(--muted)]">
                    <th className="px-3 py-2">Время</th>
                    <th className="px-3 py-2">Источник</th>
                    <th className="px-3 py-2">Статус</th>
                    <th className="px-3 py-2 text-right">Дискуссий</th>
                    <th className="px-3 py-2 text-right">Проблем</th>
                    <th className="px-3 py-2">Тип</th>
                  </tr>
                </thead>
                <tbody>
                  {history.map((entry) => (
                    <tr key={entry.id} className="border-b border-[var(--border)]/60">
                      <td className="px-3 py-2">{formatDate(entry.started_at)}</td>
                      <td className="px-3 py-2">{sourceLabel(entry.source)}</td>
                      <td className="px-3 py-2">
                        {statusBadge(entry.status)}
                        {entry.error_message && <span className="ml-2 text-xs text-[var(--danger)]" title={entry.error_message}>!</span>}
                      </td>
                      <td className="px-3 py-2 text-right">{entry.discussions_found}</td>
                      <td className="px-3 py-2 text-right">{entry.problems_created}</td>
                      <td className="px-3 py-2">{entry.triggered_by === 'schedule' ? 'Авто' : 'Ручной'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      </main>
    </div>
  );
}
