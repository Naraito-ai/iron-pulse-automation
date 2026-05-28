// lib/api.ts — Backend API client for the dashboard

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const WS_URL   = process.env.NEXT_PUBLIC_WS_URL  || 'ws://localhost:8000/ws/live';

export interface NewsStory {
  id: number;
  run_date: string;
  rank: number;
  title: string;
  summary: string;
  source: string;
  url: string;
  published_at: string;
  virality_score: number;
  keywords: string;
  selected: number;
  created_at: string;
}

export interface GeneratedPost {
  id: number;
  run_date: string;
  rank: number;
  headline: string;
  subheadline: string;
  caption: string;
  hashtags: string;
  cta: string;
  bullet_points: string[];
  slide_paths: string[];
  thumbnail_path: string;
  reel_thumb_path?: string;
  reel_thumb_url?: string;
  image_urls: string[];
  reel_url?: string;
  status: string;
  created_at: string;
}

export interface AnalyticsSnapshot {
  id: number;
  ig_media_id: string;
  likes: number;
  comments: number;
  shares: number;
  saves: number;
  reach: number;
  impressions: number;
  engagement_rate: number;
  viral_score: number;
  snapshot_at: string;
}

export interface SystemStatus {
  brand_name: string;
  demo_mode: boolean;
  instagram_connected: boolean;
  instagram_user_id?: string;
  elevenlabs_configured?: boolean;
  scheduler_active: boolean;
  next_run_at: string;
  seconds_until_next: number;
  schedule_time: string;
  last_run: Record<string, unknown> | null;
  ws_clients: number;
  server_time: string;
}

export interface AnalyticsSummary {
  total_posts: number;
  total_likes: number;
  total_comments: number;
  total_shares: number;
  total_saves: number;
  total_reach: number;
  total_impressions: number;
  avg_engagement_rate: number;
  avg_viral_score: number;
  best_viral_score: number;
  snapshots: AnalyticsSnapshot[];
}

export interface LogEntry {
  id: number;
  run_date: string;
  level: string;
  module: string;
  message: string;
  details: string;
  created_at: string;
}

async function apiFetch<T>(path: string): Promise<T> {
  const resp = await fetch(`${API_BASE}${path}`, { cache: 'no-store' });
  if (!resp.ok) throw new Error(`API ${path} failed: ${resp.status}`);
  return resp.json();
}

export const api = {
  status:    () => apiFetch<SystemStatus>('/api/status'),
  news:      () => apiFetch<{ stories: NewsStory[]; count: number }>('/api/news'),
  posts:     () => apiFetch<{ posts: GeneratedPost[]; count: number }>('/api/posts'),
  drafts:    () => apiFetch<{ drafts: GeneratedPost[]; count: number }>('/api/drafts'),
  approveDraft: (id: number) => fetch(`${API_BASE}/api/drafts/${id}/approve`, { method: 'POST' }).then(r => r.json()),
  rejectDraft:  (id: number) => fetch(`${API_BASE}/api/drafts/${id}/reject`, { method: 'POST' }).then(r => r.json()),
  editDraft:    (id: number, data: { headline: string; caption: string }) => fetch(`${API_BASE}/api/drafts/${id}`, { method: 'PUT', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(data) }).then(r => r.json()),
  generateCustom: (prompt: string) => fetch(`${API_BASE}/api/generate-custom`, { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ prompt }) }).then(r => r.json()),
  published: () => apiFetch<{ published: unknown[]; count: number }>('/api/published'),
  analytics: () => apiFetch<AnalyticsSummary>('/api/analytics'),
  logs:      (limit = 100) => apiFetch<{ logs: LogEntry[]; count: number }>(`/api/logs?limit=${limit}`),
  history:   () => apiFetch<{ history: unknown[] }>('/api/history'),
  trigger:   () => fetch(`${API_BASE}/api/trigger`, { method: 'POST' }).then(r => r.json()),
  thumbnails: () => apiFetch<{ thumbnails: { name: string; url: string }[] }>('/api/images/thumbnails'),
};

export { WS_URL, API_BASE };
