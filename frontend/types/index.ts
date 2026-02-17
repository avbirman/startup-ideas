/**
 * TypeScript types for Startup Ideas Collector API
 */

export type CardStatus = 'new' | 'viewed' | 'in_review' | 'verified' | 'archived' | 'rejected';
export type ScrapeSource = 'reddit' | 'hackernews' | 'youtube' | 'medium' | 'all';
export type AudienceType = 'consumers' | 'entrepreneurs' | 'mixed' | 'unknown';

export interface Discussion {
  id: number;
  url: string;
  title: string;
  upvotes: number;
  comments_count: number;
  source_name: string;
}

export interface StartupIdea {
  id: number;
  idea_title: string;
  description: string;
  approach: string | null;
  value_proposition: string | null;
  core_features: string[];
}

export interface MarketingAnalysis {
  tam: string | null;
  sam: string | null;
  som: string | null;
  market_description: string | null;
  positioning: string | null;
  pricing_model: string | null;
  target_segments: string[];
  gtm_channels: string[];
  competitive_moat: string | null;
  market_score: number | null;
  score_reasoning: string | null;
  competitors_count: number;
}

export interface Problem {
  id: number;
  problem_statement: string;
  severity: number | null;
  target_audience: string | null;
  audience_type: AudienceType;
  current_solutions: string | null;
  why_they_fail: string | null;
  analysis_tier: 'none' | 'basic' | 'deep';
  overall_score: number | null;
  market_score: number | null;
  ideas_count: number;
  discussion: Discussion;
  extracted_at: string;
  // Card management
  card_status: CardStatus;
  is_starred: boolean;
  view_count: number;
  user_tags: string[];
  first_viewed_at: string | null;
  last_viewed_at: string | null;
}

export interface ProblemDetail extends Problem {
  startup_ideas: StartupIdea[];
  marketing_analysis: MarketingAnalysis | null;
  user_notes: string | null;
  archived_at: string | null;
  verified_at: string | null;
}

export interface ProblemFilters {
  skip?: number;
  limit?: number;
  min_score?: number;
  analysis_tier?: 'basic' | 'deep';
  sort_by?: 'score' | 'date' | 'severity' | 'engagement';
  status?: CardStatus;
  is_starred?: boolean;
  tags?: string;
  source_type?: string;
  audience_type?: AudienceType;
  date_from?: string;
  date_to?: string;
  include_archived?: boolean;
}

export interface Stats {
  totals: {
    discussions: number;
    problems: number;
    ideas: number;
  };
  today: {
    discussions: number;
    problems: number;
  };
  analysis_tiers: {
    basic: number;
    deep: number;
  };
  score_distribution: {
    '90-100': number;
    '70-89': number;
    '50-69': number;
    '30-49': number;
    '0-29': number;
  };
  average_scores: {
    overall: number;
    market: number;
  };
  top_problems: Array<{
    id: number;
    problem_statement: string;
    score: number;
    upvotes: number;
  }>;
  sources: Array<{
    name: string;
    type: string;
    discussions_count: number;
    last_scraped: string | null;
    is_active: boolean;
  }>;
  card_statuses: Record<CardStatus, number>;
  starred_count: number;
  timestamp: string;
}

export interface Competitor {
  name: string;
  url: string;
  description: string;
}

export interface ScrapeSchedule {
  enabled: boolean;
  interval_hours: number;
  source: ScrapeSource;
  limit: number;
  analyze: boolean;
  created_at: string | null;
  last_run_at: string | null;
  next_run_at: string | null;
}

export interface ScrapeLogEntry {
  id: number;
  source: string;
  status: 'running' | 'completed' | 'failed';
  discussions_found: number;
  problems_created: number;
  error_message: string | null;
  started_at: string;
  completed_at: string | null;
  triggered_by: 'manual' | 'schedule';
}
