/**
 * API Client for Startup Ideas Collector Backend
 */

import type { Problem, ProblemDetail, ProblemFilters, Stats, Competitor, CardStatus, ScrapeSchedule, ScrapeLogEntry, ScrapeSource } from '@/types';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string = API_BASE_URL) {
    this.baseUrl = baseUrl;
  }

  private async request<T>(
    endpoint: string,
    options?: RequestInit
  ): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`;

    try {
      const response = await fetch(url, {
        ...options,
        headers: {
          'Content-Type': 'application/json',
          ...options?.headers,
        },
      });

      if (!response.ok) {
        throw new Error(`API Error: ${response.status} ${response.statusText}`);
      }

      return await response.json();
    } catch (error) {
      console.error(`API request failed: ${url}`, error);
      throw error;
    }
  }

  // Stats
  async getStats(): Promise<Stats> {
    return this.request<Stats>('/api/stats');
  }

  // Problems
  async getProblems(params?: ProblemFilters): Promise<Problem[]> {
    const queryParams = new URLSearchParams();

    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined && value !== null) {
          queryParams.append(key, String(value));
        }
      });
    }

    const query = queryParams.toString();
    return this.request<Problem[]>(`/api/problems${query ? `?${query}` : ''}`);
  }

  async getProblemDetail(id: number): Promise<ProblemDetail> {
    return this.request<ProblemDetail>(`/api/problems/${id}`);
  }

  async getProblem(id: number): Promise<ProblemDetail> {
    return this.request<ProblemDetail>(`/api/problems/${id}`);
  }

  async getArchivedProblems(params?: { skip?: number; limit?: number }): Promise<Problem[]> {
    const queryParams = new URLSearchParams();
    if (params?.skip) queryParams.append('skip', String(params.skip));
    if (params?.limit) queryParams.append('limit', String(params.limit));
    const query = queryParams.toString();
    return this.request<Problem[]>(`/api/problems/archive${query ? `?${query}` : ''}`);
  }

  async getCompetitors(problemId: number): Promise<{ competitors: Competitor[]; count: number }> {
    return this.request<{ competitors: Competitor[]; count: number }>(
      `/api/problems/${problemId}/competitors`
    );
  }

  // Card management
  async updateCardStatus(problemId: number, status: CardStatus): Promise<{ id: number; card_status: CardStatus }> {
    return this.request(`/api/problems/${problemId}/status`, {
      method: 'PATCH',
      body: JSON.stringify({ status }),
    });
  }

  async toggleStar(problemId: number, isStarred: boolean): Promise<{ id: number; is_starred: boolean }> {
    return this.request(`/api/problems/${problemId}/star`, {
      method: 'PATCH',
      body: JSON.stringify({ is_starred: isStarred }),
    });
  }

  async updateNotes(problemId: number, notes: string): Promise<{ id: number; user_notes: string }> {
    return this.request(`/api/problems/${problemId}/notes`, {
      method: 'PATCH',
      body: JSON.stringify({ user_notes: notes }),
    });
  }

  async updateTags(problemId: number, tags: string[]): Promise<{ id: number; user_tags: string[] }> {
    return this.request(`/api/problems/${problemId}/tags`, {
      method: 'PATCH',
      body: JSON.stringify({ user_tags: tags }),
    });
  }

  // Scraper
  async triggerScrape(params: {
    source?: ScrapeSource;
    limit?: number;
    analyze?: boolean;
  } = {}): Promise<{ status: string; message?: string }> {
    const queryParams = new URLSearchParams({
      source: params.source || 'all',
      limit: String(params.limit || 10),
      analyze: String(params.analyze !== false),
    });

    return this.request<{ status: string; message?: string }>(
      `/api/scrape?${queryParams.toString()}`,
      { method: 'POST' }
    );
  }

  async getSourcesStatus(): Promise<{
    sources: Array<{
      name: string;
      type: string;
      is_active: boolean;
      last_scraped: string | null;
      created_at: string;
    }>;
    count: number;
  }> {
    return this.request('/api/sources/status');
  }

  // Schedule
  async getSchedule(): Promise<ScrapeSchedule> {
    return this.request<ScrapeSchedule>('/api/schedule');
  }

  async setSchedule(params: {
    interval_hours: number;
    source: ScrapeSource;
    limit: number;
    analyze: boolean;
  }): Promise<ScrapeSchedule> {
    return this.request<ScrapeSchedule>('/api/schedule', {
      method: 'POST',
      body: JSON.stringify(params),
    });
  }

  async deleteSchedule(): Promise<{ status: string }> {
    return this.request<{ status: string }>('/api/schedule', {
      method: 'DELETE',
    });
  }

  // Scrape history
  async getScrapeHistory(limit: number = 20): Promise<ScrapeLogEntry[]> {
    return this.request<ScrapeLogEntry[]>(`/api/scrape/history?limit=${limit}`);
  }
}

export const api = new ApiClient();
export { ApiClient };
