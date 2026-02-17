'use client';

import Link from 'next/link';
import type { Problem } from '@/types';
import { StatusBadge } from './StatusBadge';
import { StarButton } from './StarButton';

interface ProblemCardProps {
  problem: Problem;
  onStarToggle?: (problemId: number, isStarred: boolean) => void;
}

const TAG_COLORS = [
  'bg-cyan-500/20 text-cyan-700 dark:text-cyan-300',
  'bg-emerald-500/20 text-emerald-700 dark:text-emerald-300',
  'bg-amber-500/20 text-amber-700 dark:text-amber-300',
  'bg-rose-500/20 text-rose-700 dark:text-rose-300',
  'bg-indigo-500/20 text-indigo-700 dark:text-indigo-300',
  'bg-teal-500/20 text-teal-700 dark:text-teal-300',
];

export function ProblemCard({ problem, onStarToggle }: ProblemCardProps) {
  const getScoreColor = (score: number | null) => {
    if (!score) return 'bg-[var(--card-2)] text-[var(--muted)]';
    if (score >= 70) return 'bg-emerald-500/20 text-emerald-700 dark:text-emerald-300';
    if (score >= 50) return 'bg-amber-500/20 text-amber-700 dark:text-amber-300';
    return 'bg-rose-500/20 text-rose-700 dark:text-rose-300';
  };

  const getTierBadge = (tier: string) => {
    if (tier === 'deep') {
      return <span className="rounded-full bg-indigo-500/20 px-2 py-1 text-xs font-medium text-indigo-700 dark:text-indigo-300">Deep</span>;
    }
    if (tier === 'basic') {
      return <span className="rounded-full bg-cyan-500/20 px-2 py-1 text-xs font-medium text-cyan-700 dark:text-cyan-300">Basic</span>;
    }
    return null;
  };

  return (
    <Link href={`/problems/${problem.id}`}>
      <div className="app-card relative cursor-pointer p-6 transition hover:-translate-y-0.5 hover:shadow-xl">
        {/* Star Button - top right */}
        <div className="absolute top-4 right-4">
          <StarButton
            problemId={problem.id}
            isStarred={problem.is_starred}
            size="sm"
            onToggle={(starred) => onStarToggle?.(problem.id, starred)}
          />
        </div>

        {/* Header */}
        <div className="flex items-start gap-4 mb-3 pr-8">
          <div className="flex-1">
            <h3 className="title-display line-clamp-2 text-lg font-semibold text-[var(--text)]">
              {problem.problem_statement}
            </h3>
          </div>

          {/* Score Badge */}
          {problem.overall_score !== null && (
            <div className={`flex-shrink-0 px-3 py-1 rounded-full font-bold text-sm ${getScoreColor(problem.overall_score)}`}>
              {problem.overall_score}/100
            </div>
          )}
        </div>

        {/* Status + Tags row */}
        <div className="flex flex-wrap items-center gap-2 mb-3">
          <StatusBadge status={problem.card_status} />
          {problem.user_tags?.map((tag, i) => (
            <span
              key={tag}
              className={`px-2 py-0.5 rounded-full text-xs font-medium ${TAG_COLORS[i % TAG_COLORS.length]}`}
            >
              {tag}
            </span>
          ))}
        </div>

        {/* Metadata */}
        <div className="mb-3 flex flex-wrap gap-3 text-sm text-[var(--muted)]">
          {problem.target_audience && (
            <div className="flex items-center gap-1">
              <span>👥</span>
              <span>{problem.target_audience}</span>
            </div>
          )}
          {problem.severity && (
            <div className="flex items-center gap-1">
              <span>🔥</span>
              <span>Критичность: {problem.severity}/10</span>
            </div>
          )}
          <div className="flex items-center gap-1">
            <span>💡</span>
            <span>{problem.ideas_count} {problem.ideas_count === 1 ? 'идея' : problem.ideas_count < 5 ? 'идеи' : 'идей'}</span>
          </div>
          {problem.view_count > 0 && (
            <div className="flex items-center gap-1">
              <span>👁</span>
              <span>{problem.view_count}</span>
            </div>
          )}
        </div>

        {/* Discussion Source */}
        <div className="flex items-center justify-between text-sm">
          <div className="flex items-center gap-2 text-[var(--muted)]">
            <span className="font-medium">{problem.discussion.source_name}</span>
            <span>•</span>
            <span>↑ {problem.discussion.upvotes}</span>
            <span>•</span>
            <span>💬 {problem.discussion.comments_count}</span>
          </div>
          {getTierBadge(problem.analysis_tier)}
        </div>
      </div>
    </Link>
  );
}
