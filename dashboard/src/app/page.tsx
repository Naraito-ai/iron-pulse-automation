'use client';

import React, { useState, useEffect, useCallback, useRef } from 'react';
import { api, SystemStatus, AnalyticsSummary, LogEntry, API_BASE } from '@/lib/api';

// ─── Types ───────────────────────────────────────────────────────────────────
interface PublishedPost {
  id: number;
  ig_media_id: string;
  ig_permalink: string;
  status: string;
  published_at: string;
  headline?: string;
  caption?: string;
  content_type?: string;
  post_format?: string;
}

interface TokenStatus {
  status: string;
  days_remaining: number;
  message: string;
  expires_at?: string;
}

type Section = 'overview' | 'drafts' | 'published' | 'analytics' | 'logs';

interface ScheduleSlot {
  rank: number;
  content_type: string;
  time: string;
  next_fire: string;
  seconds_until: number;
}

const CONTENT_TYPE_META: Record<string, { icon: string; label: string; color: string }> = {
  hot_take:       { icon: '🔥', label: 'Hot Take',      color: '#FF4444' },
  quick_tip:      { icon: '⚡', label: 'Quick Tip',     color: '#FFB400' },
  save_list:      { icon: '📋', label: 'Save List',     color: '#00CFFF' },
  myth_buster:    { icon: '🧠', label: 'Myth Buster',   color: '#A855F7' },
  meme_relatable: { icon: '😂', label: 'Gym Meme',      color: '#00FF88' },
  transformation: { icon: '💪', label: 'Transformation', color: '#FF6B00' },
};

// ─── Helpers ─────────────────────────────────────────────────────────────────
function fmt(n: number) {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000)     return `${(n / 1_000).toFixed(1)}K`;
  return String(n);
}
function timeAgo(iso: string) {
  const diff = Date.now() - new Date(iso).getTime();
  const m = Math.floor(diff / 60000);
  if (m < 1)  return 'just now';
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  return `${Math.floor(h / 24)}d ago`;
}

// ─── Main ────────────────────────────────────────────────────────────────────
export default function Dashboard() {
  const [section,     setSection]     = useState<Section>('overview');
  const [status,      setStatus]      = useState<SystemStatus | null>(null);
  const [analytics,   setAnalytics]   = useState<AnalyticsSummary | null>(null);
  const [logs,        setLogs]        = useState<LogEntry[]>([]);
  const [drafts,      setDrafts]      = useState<any[]>([]);
  const [published,   setPublished]   = useState<PublishedPost[]>([]);
  const [tokenStatus, setTokenStatus] = useState<TokenStatus | null>(null);
  const [schedule,    setSchedule]    = useState<ScheduleSlot[]>([]);
  const [loading,     setLoading]     = useState(true);
  const [triggering,  setTriggering]  = useState(false);
  const [triggerMsg,  setTriggerMsg]  = useState('');
  const [newToken,    setNewToken]    = useState('');
  const [tokenSaving, setTokenSaving] = useState(false);
  const [tokenMsg,    setTokenMsg]    = useState('');
  const logsRef = useRef<HTMLDivElement>(null);

  const loadData = useCallback(async () => {
    try {
      const [sRes, aRes, lRes, pRes, tRes, dRes, schRes] = await Promise.allSettled([
        api.status(),
        api.analytics(),
        api.logs(120),
        fetch('/api/published').then(r => r.json()),
        fetch('/api/token-status').then(r => r.json()),
        api.drafts(),
        fetch('/api/schedule').then(r => r.json()),
      ]);
      if (sRes.status === 'fulfilled') setStatus(sRes.value);
      if (aRes.status === 'fulfilled') setAnalytics(aRes.value);
      if (lRes.status === 'fulfilled') setLogs(lRes.value.logs);
      if (pRes.status === 'fulfilled') setPublished((pRes.value as any).published ?? []);
      if (tRes.status === 'fulfilled') setTokenStatus(tRes.value);
      if (dRes.status === 'fulfilled') setDrafts(dRes.value.drafts ?? []);
      if (schRes.status === 'fulfilled') setSchedule((schRes.value as any).schedule ?? []);
    } finally { setLoading(false); }
  }, []);

  useEffect(() => {
    loadData();
    const t = setInterval(loadData, 15000);
    return () => clearInterval(t);
  }, [loadData]);

  // WebSocket live logs
  useEffect(() => {
    const wsUrl = API_BASE.replace('https://', 'wss://').replace('http://', 'ws://');
    const ws = new WebSocket(`${wsUrl}/ws/live`);
    ws.onmessage = (e) => {
      try {
        const msg = JSON.parse(e.data);
        if (msg.type === 'log' || msg.level) {
          setLogs(prev => [msg, ...prev].slice(0, 200));
          // Auto-refresh drafts when a custom post is done
          if (msg.message?.includes('saved to Drafts')) loadData();
        }
      } catch {}
    };
    return () => ws.close();
  }, [loadData]);

  // Auto-scroll logs
  useEffect(() => {
    if (section === 'logs' && logsRef.current) {
      logsRef.current.scrollTop = 0;
    }
  }, [logs, section]);

  const handleTrigger = async () => {
    setTriggering(true);
    setTriggerMsg('');
    try {
      await fetch('/api/trigger', { method: 'POST' });
      setTriggerMsg('✅ Pipeline started!');
      setSection('logs');
      setTimeout(loadData, 3000);
    } catch {
      setTriggerMsg('❌ Failed — is backend running?');
    } finally {
      setTriggering(false);
      setTimeout(() => setTriggerMsg(''), 8000);
    }
  };

  const handleSaveToken = async () => {
    if (!newToken.trim()) return;
    setTokenSaving(true);
    try {
      const res = await fetch('/api/update-token', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token: newToken.trim() }),
      });
      const d = await res.json();
      setTokenMsg(res.ok ? '✅ Token saved!' : `❌ ${d.error}`);
      if (res.ok) { setNewToken(''); setTimeout(loadData, 1000); }
    } catch { setTokenMsg('❌ Failed to save.'); }
    finally {
      setTokenSaving(false);
      setTimeout(() => setTokenMsg(''), 6000);
    }
  };

  const tokenColor =
    tokenStatus?.status === 'expired'  ? '#FF3250' :
    tokenStatus?.status === 'critical' ? '#FF3250' :
    tokenStatus?.status === 'warning'  ? '#FFB400' : '#00FF88';

  const livePublished  = published.filter(p => p.status === 'published');
  const failedPosts    = published.filter(p => p.status === 'failed');
  const successRate    = published.length ? Math.round((livePublished.length / published.length) * 100) : 0;

  const NAV: { id: Section; icon: string; label: string }[] = [
    { id: 'overview',  icon: '🏠', label: 'Overview'  },
    { id: 'drafts',    icon: '📝', label: 'Today\'s Drafts' },
    { id: 'published', icon: '📸', label: 'Published Posts' },
    { id: 'analytics', icon: '📊', label: 'Analytics' },
    { id: 'logs',      icon: '📋', label: 'Live Logs' },
  ];

  return (
    <div style={{ display: 'flex', minHeight: '100vh', background: '#080808', color: '#fff', fontFamily: 'var(--font-sans, Inter, sans-serif)' }}>

      {/* ─── Sidebar ──────────────────────────────────────────────────────── */}
      <aside style={{
        width: 240, flexShrink: 0, background: '#0f0f0f',
        borderRight: '1px solid rgba(255,255,255,0.06)',
        display: 'flex', flexDirection: 'column', padding: '24px 16px',
        position: 'sticky', top: 0, height: '100vh', overflowY: 'auto',
      }}>
        {/* Brand */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 28 }}>
          <div style={{
            width: 38, height: 38, borderRadius: 12,
            background: 'linear-gradient(135deg, #FF5500, #FF0080)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: 18, boxShadow: '0 0 20px rgba(255,85,0,0.4)',
          }}>⚡</div>
          <div>
            <div style={{ fontWeight: 800, fontSize: 15, letterSpacing: '-0.3px' }}>Iron Pulse</div>
            <div style={{ fontSize: 10, color: '#555', marginTop: 1 }}>Fitness Automation</div>
          </div>
        </div>

        {/* Status dots */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6, marginBottom: 24 }}>
          {[
            { label: 'API Online',    ok: !loading },
            { label: 'Instagram',     ok: status?.instagram_connected ?? false },
            { label: `${livePublished.length} Live Posts`, ok: livePublished.length > 0 },
          ].map(({ label, ok }) => (
            <div key={label} style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 11 }}>
              <div style={{
                width: 7, height: 7, borderRadius: '50%',
                background: ok ? '#00FF88' : '#333',
                boxShadow: ok ? '0 0 6px #00FF88' : 'none',
                flexShrink: 0,
              }} />
              <span style={{ color: ok ? '#aaa' : '#444' }}>{label}</span>
            </div>
          ))}
        </div>

        {/* Nav */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 4, marginBottom: 'auto' }}>
          {NAV.map(n => (
            <button key={n.id} onClick={() => setSection(n.id)} style={{
              display: 'flex', alignItems: 'center', gap: 10,
              padding: '9px 12px', borderRadius: 10, border: 'none', cursor: 'pointer',
              background: section === n.id ? 'rgba(255,85,0,0.12)' : 'transparent',
              color: section === n.id ? '#FF5500' : '#666',
              fontWeight: section === n.id ? 700 : 500,
              fontSize: 13, textAlign: 'left', transition: 'all 0.15s',
            }}>
              <span>{n.icon}</span>{n.label}
              {n.id === 'logs' && logs.length > 0 && (
                <span style={{
                  marginLeft: 'auto', background: '#FF5500', color: '#fff',
                  borderRadius: 20, fontSize: 9, padding: '1px 6px', fontWeight: 700,
                }}>LIVE</span>
              )}
            </button>
          ))}
        </div>

        {/* Run button */}
        <div style={{ marginTop: 24, paddingTop: 20, borderTop: '1px solid rgba(255,255,255,0.06)' }}>
          <button onClick={handleTrigger} disabled={triggering} style={{
            width: '100%', padding: '10px 0', borderRadius: 10, border: 'none',
            background: triggering ? '#222' : 'linear-gradient(135deg, #FF5500, #FF0080)',
            color: '#fff', fontWeight: 700, fontSize: 13, cursor: triggering ? 'not-allowed' : 'pointer',
            boxShadow: triggering ? 'none' : '0 0 20px rgba(255,85,0,0.3)',
            transition: 'all 0.2s',
          }}>
            {triggering ? '⏳ Running...' : '▶ Run Now'}
          </button>
          {triggerMsg && <div style={{ fontSize: 11, textAlign: 'center', marginTop: 6, color: triggerMsg.startsWith('✅') ? '#00FF88' : '#FF3250' }}>{triggerMsg}</div>}
          <div style={{ fontSize: 10, color: '#333', textAlign: 'center', marginTop: 6 }}>
            Auto at {status?.schedule_time ?? '09:00'} IST daily
          </div>

          {/* Token widget */}
          <div style={{
            marginTop: 14, padding: '10px 12px', borderRadius: 10,
            background: `${tokenColor}10`,
            border: `1px solid ${tokenColor}30`,
          }}>
            <div style={{ fontSize: 11, fontWeight: 700, color: tokenColor, marginBottom: 4 }}>
              🔑 Token: {
                tokenStatus?.status === 'expired'  ? 'EXPIRED ❌' :
                tokenStatus?.status === 'critical' ? `${tokenStatus.days_remaining}d — CRITICAL` :
                tokenStatus?.status === 'warning'  ? `${tokenStatus.days_remaining}d ⚠️` :
                tokenStatus?.status === 'permanent'? 'Never expires ♾️' :
                tokenStatus ? `${tokenStatus.days_remaining}d left ✅` : '...'
              }
            </div>
            {(tokenStatus?.status === 'expired' || tokenStatus?.status === 'critical' || tokenStatus?.status === 'warning') && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 5 }}>
                <textarea value={newToken} onChange={e => setNewToken(e.target.value)}
                  placeholder="Paste new token..."
                  style={{
                    width: '100%', height: 50, fontSize: 9, padding: '4px 6px',
                    background: '#111', border: '1px solid #222', borderRadius: 6,
                    color: '#aaa', resize: 'none', fontFamily: 'monospace',
                  }} />
                <button onClick={handleSaveToken} disabled={tokenSaving || !newToken.trim()} style={{
                  padding: '6px 0', borderRadius: 7, border: 'none',
                  background: '#FF5500', color: '#fff', fontSize: 11, fontWeight: 700,
                  cursor: 'pointer', opacity: tokenSaving || !newToken.trim() ? 0.5 : 1,
                }}>
                  {tokenSaving ? 'Saving...' : '💾 Save Token'}
                </button>
                {tokenMsg && <div style={{ fontSize: 10, color: tokenMsg.startsWith('✅') ? '#00FF88' : '#FF3250' }}>{tokenMsg}</div>}
              </div>
            )}
          </div>
        </div>
      </aside>

      {/* ─── Main ─────────────────────────────────────────────────────────── */}
      <main style={{ flex: 1, padding: '32px 36px', overflowY: 'auto', maxHeight: '100vh' }}>
        {loading ? <LoadingScreen /> : (
          <>
            {section === 'overview'  && <OverviewSection status={status} analytics={analytics} published={published} livePublished={livePublished} successRate={successRate} schedule={schedule} />}
            {section === 'drafts'    && <DraftsSection drafts={drafts} onUpdate={loadData} />}
            {section === 'published' && <PublishedSection published={published} />}
            {section === 'analytics' && <AnalyticsSection analytics={analytics} />}
            {section === 'logs'      && <LogsSection logs={logs} logsRef={logsRef} />}
          </>
        )}
      </main>
    </div>
  );
}

// ─── Loading ─────────────────────────────────────────────────────────────────
function LoadingScreen() {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '80vh', gap: 16 }}>
      <div style={{ width: 48, height: 48, border: '3px solid #222', borderTop: '3px solid #FF5500', borderRadius: '50%', animation: 'spin 0.8s linear infinite' }} />
      <div style={{ color: '#444', fontSize: 14 }}>Loading dashboard...</div>
      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  );
}

// ─── Overview ────────────────────────────────────────────────────────────────
function OverviewSection({ status, analytics, published, livePublished, successRate, schedule }: {
  status: SystemStatus | null;
  analytics: AnalyticsSummary | null;
  published: PublishedPost[];
  livePublished: PublishedPost[];
  successRate: number;
  schedule: ScheduleSlot[];
}) {
  const reels     = livePublished.filter(p => p.ig_permalink?.includes('/reel/'));
  const carousels = livePublished.filter(p => p.ig_permalink?.includes('/p/'));

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 28 }}>
      {/* Header */}
      <div>
        <h1 style={{ fontSize: 32, fontWeight: 900, margin: 0, background: 'linear-gradient(90deg, #fff, #666)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
          Mission Control 🏋️
        </h1>
        <p style={{ color: '#444', fontSize: 13, margin: '6px 0 0' }}>Iron Pulse — Viral Fitness Content Automation</p>
      </div>

      {/* KPI row */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 14 }}>
        {[
          { label: 'Live Posts',   value: livePublished.length, color: '#00FF88', sub: `${reels.length} Reels · ${carousels.length} Carousels` },
          { label: 'Total Reach',  value: analytics ? fmt(analytics.total_reach) : '—', color: '#FF5500', sub: 'Across all posts' },
          { label: 'Avg Engagement', value: analytics ? `${analytics.avg_engagement_rate}%` : '—', color: '#FFB400', sub: 'Likes + Comments + Saves' },
          { label: 'Success Rate', value: `${successRate}%`, color: '#A855F7', sub: `${livePublished.length}/${published.length} published` },
        ].map(({ label, value, color, sub }) => (
          <div key={label} style={{ background: '#111', border: '1px solid #1a1a1a', borderRadius: 14, padding: '18px 20px' }}>
            <div style={{ fontSize: 11, color: '#444', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 8 }}>{label}</div>
            <div style={{ fontSize: 28, fontWeight: 900, color, lineHeight: 1 }}>{value}</div>
            <div style={{ fontSize: 11, color: '#333', marginTop: 6 }}>{sub}</div>
          </div>
        ))}
      </div>

      {/* Content type breakdown */}
      <div style={{ background: '#111', border: '1px solid #1a1a1a', borderRadius: 14, padding: 24 }}>
        <div style={{ fontSize: 13, fontWeight: 700, marginBottom: 16, color: '#888' }}>TODAY'S CONTENT MIX</div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 10 }}>
          {Object.entries(CONTENT_TYPE_META).map(([type, meta]) => (
            <div key={type} style={{
              display: 'flex', alignItems: 'center', gap: 10, padding: '10px 14px',
              background: `${meta.color}0a`, border: `1px solid ${meta.color}20`, borderRadius: 10,
            }}>
              <span style={{ fontSize: 20 }}>{meta.icon}</span>
              <div>
                <div style={{ fontSize: 12, fontWeight: 700, color: meta.color }}>{meta.label}</div>
                <div style={{ fontSize: 10, color: '#444' }}>
                  {type === 'hot_take' || type === 'quick_tip' || type === 'meme_relatable' ? 'Reel' : 'Carousel'}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Recent published */}
      {livePublished.length > 0 && (
        <div style={{ background: '#111', border: '1px solid #1a1a1a', borderRadius: 14, padding: 24 }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
            <div style={{ fontSize: 13, fontWeight: 700, color: '#888' }}>LATEST POSTS</div>
            <span style={{ background: '#00FF8820', color: '#00FF88', fontSize: 10, fontWeight: 700, padding: '3px 10px', borderRadius: 20 }}>
              {livePublished.length} LIVE
            </span>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {livePublished.slice(0, 5).map(post => (
              <PostRow key={post.id} post={post} />
            ))}
          </div>
        </div>
      )}

      {/* Today's Posting Schedule */}
      <div style={{ background: '#111', border: '1px solid #1a1a1a', borderRadius: 14, padding: 24 }}>
        <div style={{ fontSize: 13, fontWeight: 700, color: '#888', marginBottom: 16 }}>TODAY'S SCHEDULE</div>
        {schedule.length === 0 ? (
          <div style={{ color: '#333', fontSize: 12 }}>Schedule data loading...</div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {schedule.map(slot => {
              const meta = CONTENT_TYPE_META[slot.content_type] ?? { icon: '📄', label: slot.content_type, color: '#666' };
              const minsUntil = Math.round(slot.seconds_until / 60);
              const hoursUntil = Math.floor(minsUntil / 60);
              const label = hoursUntil > 0 ? `in ${hoursUntil}h ${minsUntil % 60}m` : `in ${minsUntil}m`;
              return (
                <div key={slot.rank} style={{
                  display: 'flex', alignItems: 'center', gap: 14,
                  background: '#161616', borderRadius: 10, padding: '12px 16px',
                  border: `1px solid ${meta.color}20`,
                }}>
                  <span style={{ fontSize: 20, flexShrink: 0 }}>{meta.icon}</span>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontSize: 13, fontWeight: 700, color: '#ddd' }}>{meta.label}</div>
                    <div style={{ fontSize: 11, color: '#444', marginTop: 2 }}>Posts at {slot.time}</div>
                  </div>
                  <span style={{
                    fontSize: 10, fontWeight: 700, padding: '3px 10px', borderRadius: 20,
                    background: `${meta.color}15`, color: meta.color,
                  }}>{label}</span>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}

// ─── Post Row ─────────────────────────────────────────────────────────────────
function PostRow({ post }: { post: PublishedPost }) {
  const type  = post.content_type ?? '';
  const meta  = CONTENT_TYPE_META[type] ?? { icon: '📄', label: type, color: '#666' };
  const isReel = post.ig_permalink?.includes('/reel/');

  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 12, padding: '10px 14px',
      background: '#161616', borderRadius: 10, border: '1px solid #1e1e1e',
    }}>
      <span style={{ fontSize: 22, flexShrink: 0 }}>{meta.icon}</span>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontSize: 13, fontWeight: 600, color: '#ddd', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          {post.headline ?? post.caption?.slice(0, 60) ?? 'Untitled'}
        </div>
        <div style={{ fontSize: 11, color: '#444', marginTop: 2 }}>
          {timeAgo(post.published_at)} · {isReel ? '🎬 Reel' : '🖼️ Carousel'}
        </div>
      </div>
      <span style={{
        fontSize: 10, fontWeight: 700, padding: '3px 8px', borderRadius: 6,
        background: `${meta.color}15`, color: meta.color, flexShrink: 0,
      }}>{meta.label}</span>
      {post.ig_permalink && (
        <a href={post.ig_permalink} target="_blank" rel="noreferrer" style={{
          fontSize: 11, color: '#FF5500', textDecoration: 'none', fontWeight: 700, flexShrink: 0,
        }}>View →</a>
      )}
    </div>
  );
}

// ─── Published Posts ──────────────────────────────────────────────────────────
function PublishedSection({ published }: { published: PublishedPost[] }) {
  const live   = published.filter(p => p.status === 'published');
  const failed = published.filter(p => p.status === 'failed');

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
      <div>
        <h1 style={{ fontSize: 26, fontWeight: 900, margin: 0 }}>📸 Published Posts</h1>
        <p style={{ color: '#444', fontSize: 13, margin: '6px 0 0' }}>{live.length} live · {failed.length} failed</p>
      </div>

      {/* Live posts */}
      {live.length > 0 && (
        <div>
          <div style={{ fontSize: 12, fontWeight: 700, color: '#00FF88', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 12 }}>
            ✅ Live on Instagram ({live.length})
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {live.map(post => {
              const type  = post.content_type ?? '';
              const meta  = CONTENT_TYPE_META[type] ?? { icon: '📄', label: type || 'Post', color: '#666' };
              const isReel = post.ig_permalink?.includes('/reel/');
              return (
                <div key={post.id} style={{
                  display: 'flex', alignItems: 'center', gap: 14,
                  background: '#111', border: '1px solid #1a1a1a', borderRadius: 12, padding: '14px 18px',
                }}>
                  <div style={{
                    width: 44, height: 44, borderRadius: 10, flexShrink: 0,
                    background: `linear-gradient(135deg, ${meta.color}30, ${meta.color}10)`,
                    border: `1px solid ${meta.color}30`,
                    display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 22,
                  }}>{meta.icon}</div>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontSize: 14, fontWeight: 700, color: '#ddd', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {post.headline ?? post.caption?.slice(0, 70) ?? '—'}
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginTop: 4, flexWrap: 'wrap' }}>
                      <span style={{ fontSize: 10, color: meta.color, fontWeight: 700, background: `${meta.color}15`, padding: '2px 8px', borderRadius: 5 }}>{meta.label}</span>
                      <span style={{ fontSize: 10, color: '#444' }}>{isReel ? '🎬 Reel' : '🖼️ Carousel'}</span>
                      <span style={{ fontSize: 10, color: '#333' }}>{timeAgo(post.published_at)}</span>
                      <span style={{ fontSize: 10, color: '#333', fontFamily: 'monospace' }}>{post.ig_media_id}</span>
                    </div>
                  </div>
                  <a href={post.ig_permalink} target="_blank" rel="noreferrer" style={{
                    padding: '7px 14px', background: 'linear-gradient(135deg, #FF5500, #FF0080)',
                    borderRadius: 8, color: '#fff', fontWeight: 700, fontSize: 12,
                    textDecoration: 'none', flexShrink: 0, whiteSpace: 'nowrap',
                  }}>Open on IG →</a>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Empty state */}
      {live.length === 0 && (
        <div style={{ textAlign: 'center', padding: '60px 20px', color: '#333' }}>
          <div style={{ fontSize: 48, marginBottom: 12 }}>📭</div>
          <div style={{ fontSize: 16, fontWeight: 700, marginBottom: 6, color: '#555' }}>No live posts yet</div>
          <div style={{ fontSize: 13 }}>Click "Run Now" in the sidebar to publish your first batch</div>
        </div>
      )}
    </div>
  );
}

// ─── Analytics ───────────────────────────────────────────────────────────────
function AnalyticsSection({ analytics }: { analytics: AnalyticsSummary | null }) {
  if (!analytics) return <div style={{ color: '#444', padding: 40, textAlign: 'center' }}>No analytics yet. Posts need to be live for at least 30 minutes.</div>;

  const stats = [
    { label: 'Total Reach',      value: fmt(analytics.total_reach),       icon: '👁️',  color: '#FF5500' },
    { label: 'Total Likes',      value: fmt(analytics.total_likes),       icon: '❤️',  color: '#FF0080' },
    { label: 'Total Comments',   value: fmt(analytics.total_comments),    icon: '💬',  color: '#FFB400' },
    { label: 'Total Saves',      value: fmt(analytics.total_saves),       icon: '🔖',  color: '#00CFFF' },
    { label: 'Avg Engagement',   value: `${analytics.avg_engagement_rate}%`, icon: '📈', color: '#00FF88' },
    { label: 'Best Viral Score', value: `${analytics.best_viral_score}/10`,  icon: '🔥', color: '#A855F7' },
  ];

  const snapshots = [...(analytics.snapshots ?? [])].sort((a, b) =>
    new Date(b.snapshot_at).getTime() - new Date(a.snapshot_at).getTime()
  );

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
      <div>
        <h1 style={{ fontSize: 26, fontWeight: 900, margin: 0 }}>📊 Analytics</h1>
        <p style={{ color: '#444', fontSize: 13, margin: '6px 0 0' }}>Live data from {analytics.total_posts} published posts · refreshed every 6h</p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 14 }}>
        {stats.map(({ label, value, icon, color }) => (
          <div key={label} style={{ background: '#111', border: '1px solid #1a1a1a', borderRadius: 14, padding: '18px 20px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 10 }}>
              <span style={{ fontSize: 18 }}>{icon}</span>
              <span style={{ fontSize: 11, color: '#444', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em' }}>{label}</span>
            </div>
            <div style={{ fontSize: 30, fontWeight: 900, color }}>{value}</div>
          </div>
        ))}
      </div>

      {/* Per-post table */}
      {snapshots.length > 0 && (
        <div style={{ background: '#111', border: '1px solid #1a1a1a', borderRadius: 14, padding: 24 }}>
          <div style={{ fontSize: 13, fontWeight: 700, color: '#888', marginBottom: 16 }}>PER-POST PERFORMANCE</div>
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
              <thead>
                <tr>
                  {['Media ID', 'Reach', 'Likes', 'Comments', 'Saves', 'Engagement', 'Viral Score'].map(h => (
                    <th key={h} style={{ padding: '8px 12px', textAlign: 'left', color: '#444', fontWeight: 600, borderBottom: '1px solid #1a1a1a' }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {snapshots.map((s, i) => (
                  <tr key={s.id} style={{ background: i % 2 ? '#0d0d0d' : 'transparent' }}>
                    <td style={{ padding: '8px 12px', color: '#555', fontFamily: 'monospace', fontSize: 10 }}>{s.ig_media_id.slice(-8)}...</td>
                    <td style={{ padding: '8px 12px', color: '#FF5500', fontWeight: 700 }}>{fmt(s.reach)}</td>
                    <td style={{ padding: '8px 12px', color: '#FF0080' }}>{fmt(s.likes)}</td>
                    <td style={{ padding: '8px 12px', color: '#FFB400' }}>{fmt(s.comments)}</td>
                    <td style={{ padding: '8px 12px', color: '#00CFFF' }}>{fmt(s.saves)}</td>
                    <td style={{ padding: '8px 12px', color: '#00FF88', fontWeight: 700 }}>{s.engagement_rate}%</td>
                    <td style={{ padding: '8px 12px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                        <div style={{ flex: 1, height: 4, background: '#1a1a1a', borderRadius: 2, overflow: 'hidden' }}>
                          <div style={{ width: `${(s.viral_score / 10) * 100}%`, height: '100%', background: '#FF5500', borderRadius: 2 }} />
                        </div>
                        <span style={{ color: '#FF5500', fontWeight: 700, fontSize: 11, flexShrink: 0 }}>{s.viral_score}</span>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

// ─── Logs ────────────────────────────────────────────────────────────────────
function LogsSection({ logs, logsRef }: { logs: LogEntry[]; logsRef: React.RefObject<HTMLDivElement | null> }) {
  const LOG_COLORS: Record<string, string> = {
    ERROR:   '#FF3250', WARNING: '#FFB400', SUCCESS: '#00FF88',
    INFO:    '#aaa',    DEBUG:   '#444',
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20, height: '100%' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div>
          <h1 style={{ fontSize: 26, fontWeight: 900, margin: 0 }}>📋 Live Logs</h1>
          <p style={{ color: '#444', fontSize: 13, margin: '6px 0 0' }}>Real-time pipeline activity via WebSocket</p>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 11, color: '#00FF88' }}>
          <div style={{ width: 7, height: 7, borderRadius: '50%', background: '#00FF88', boxShadow: '0 0 8px #00FF88', animation: 'pulse 2s infinite' }} />
          LIVE
        </div>
      </div>

      <div ref={logsRef} style={{
        background: '#0a0a0a', border: '1px solid #1a1a1a', borderRadius: 14,
        padding: '16px', overflowY: 'auto', maxHeight: 'calc(100vh - 200px)',
        fontFamily: 'monospace',
      }}>
        {logs.length === 0 ? (
          <div style={{ color: '#333', textAlign: 'center', padding: 40 }}>No logs yet. Run the pipeline to see activity.</div>
        ) : (
          logs.map((log, i) => (
            <div key={log.id ?? i} style={{
              display: 'flex', gap: 12, padding: '4px 0',
              borderBottom: '1px solid #111', alignItems: 'flex-start',
            }}>
              <span style={{ color: '#333', fontSize: 10, flexShrink: 0, marginTop: 2, minWidth: 52 }}>
                {log.created_at ? new Date(log.created_at).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', second: '2-digit' }) : ''}
              </span>
              <span style={{
                fontSize: 9, fontWeight: 800, padding: '2px 6px', borderRadius: 4, flexShrink: 0, marginTop: 1,
                background: `${LOG_COLORS[log.level] ?? '#444'}15`,
                color: LOG_COLORS[log.level] ?? '#666', minWidth: 52, textAlign: 'center',
              }}>{log.level}</span>
              <span style={{ fontSize: 10, color: '#555', flexShrink: 0, minWidth: 80 }}>{log.module}</span>
              <span style={{ fontSize: 12, color: LOG_COLORS[log.level] === '#aaa' ? '#888' : LOG_COLORS[log.level], flex: 1, lineHeight: 1.4 }}>
                {log.message}
              </span>
            </div>
          ))
        )}
      </div>
      <style>{`@keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.4} }`}</style>
    </div>
  );
}

// ─── Drafts ──────────────────────────────────────────────────────────────────
function DraftsSection({ drafts, onUpdate }: { drafts: any[]; onUpdate: () => void }) {
  const [prompt, setPrompt] = useState('');
  const [generating, setGenerating] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editData, setEditData] = useState({ headline: '', caption: '' });

  const handleApprove = async (id: number) => {
    await api.approveDraft(id);
    onUpdate();
  };
  const handleReject = async (id: number) => {
    await api.rejectDraft(id);
    onUpdate();
  };
  const handleGenerate = async () => {
    if (!prompt.trim()) return;
    setGenerating(true);
    try {
      await api.generateCustom(prompt);
      setPrompt('');
      setTimeout(onUpdate, 5000);
    } finally {
      setGenerating(false);
    }
  };
  const startEditing = (draft: any) => {
    setEditingId(draft.id);
    setEditData({ headline: draft.headline || '', caption: draft.caption || '' });
  };
  const saveEditing = async (id: number) => {
    await api.editDraft(id, editData);
    setEditingId(null);
    onUpdate();
  };

  const pendingCount = drafts.filter(d => d.status === 'draft').length;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
      <div>
        <h1 style={{ fontSize: 26, fontWeight: 900, margin: 0 }}>📝 Today's Drafts</h1>
        <p style={{ color: '#444', fontSize: 13, margin: '6px 0 0' }}>{pendingCount} awaiting approval (Auto-publishes if ignored)</p>
      </div>

      <div style={{ display: 'flex', gap: 10, background: '#111', padding: '16px', borderRadius: 14, border: '1px solid #1a1a1a' }}>
        <input 
          value={prompt} onChange={e => setPrompt(e.target.value)} 
          placeholder="Enter a custom prompt (e.g. 'Benefits of creatine vs whey')..." 
          style={{ flex: 1, background: '#0a0a0a', border: '1px solid #222', padding: '12px 16px', borderRadius: 8, color: '#fff', fontSize: 14 }}
        />
        <button 
          onClick={handleGenerate} disabled={generating || !prompt.trim()}
          style={{ background: 'linear-gradient(135deg, #FF5500, #FF0080)', color: '#fff', border: 'none', padding: '0 24px', borderRadius: 8, fontWeight: 700, cursor: generating ? 'not-allowed' : 'pointer', opacity: generating ? 0.7 : 1 }}
        >
          {generating ? 'Generating...' : '✨ Generate Post'}
        </button>
      </div>

      {drafts.length === 0 ? (
        <div style={{ textAlign: 'center', padding: '60px 20px', color: '#333' }}>
          <div style={{ fontSize: 48, marginBottom: 12 }}>📭</div>
          <div style={{ fontSize: 16, fontWeight: 700, marginBottom: 6, color: '#555' }}>No drafts available</div>
          <div style={{ fontSize: 13 }}>Drafts are generated automatically at 4:00 AM. Click "Run Now" to trigger them immediately.</div>
        </div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: 16 }}>
          {drafts.map((draft, i) => {
            const isApproved = draft.status === 'approved';
            const isRejected = draft.status === 'rejected';
            const isReel = !!draft.reel_url;
            return (
              <div key={draft.id} style={{
                background: '#111', border: `1px solid ${isApproved ? '#00FF8850' : isRejected ? '#FF325050' : '#1a1a1a'}`,
                borderRadius: 14, overflow: 'hidden', display: 'flex', flexDirection: 'column',
              }}>
                {/* Media Preview */}
                <div style={{ height: 200, background: '#000', position: 'relative' }}>
                  {isReel ? (
                    <video 
                      src={`${API_BASE}${draft.reel_url}`} 
                      poster={draft.reel_thumb_url || undefined}
                      autoPlay loop muted 
                      style={{ width: '100%', height: '100%', objectFit: 'cover' }} 
                    />
                  ) : (
                    <img src={`${API_BASE}${draft.image_urls[0]}`} style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
                  )}
                  <div style={{ position: 'absolute', top: 10, left: 10, background: 'rgba(0,0,0,0.7)', padding: '4px 8px', borderRadius: 6, fontSize: 10, fontWeight: 700, color: '#fff' }}>
                    {isReel ? '🎬 REEL' : '🖼️ CAROUSEL'}
                  </div>
                  <div style={{ position: 'absolute', top: 10, right: 10, background: isApproved ? '#00FF88' : isRejected ? '#FF3250' : '#FFB400', color: '#000', padding: '4px 8px', borderRadius: 6, fontSize: 10, fontWeight: 900, textTransform: 'uppercase' }}>
                    {draft.status}
                  </div>
                  {isReel && (
                    <div style={{
                      position: 'absolute', bottom: 10, left: '50%', transform: 'translateX(-50%)',
                      background: 'rgba(0,0,0,0.75)', backdropFilter: 'blur(8px)',
                      border: '1px solid rgba(255,255,255,0.15)',
                      padding: '5px 14px', borderRadius: 20,
                      fontSize: 10, fontWeight: 700, color: '#fff', whiteSpace: 'nowrap',
                    }}>
                      🎵 Add Trending Audio for 5× Reach
                    </div>
                  )}
                </div>

                {/* Content */}
                <div style={{ padding: 16, display: 'flex', flexDirection: 'column', flex: 1 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                    <div style={{ fontSize: 10, color: '#888', fontWeight: 700 }}>POST #{draft.rank === 999 ? 'CUSTOM' : draft.rank + 1}</div>
                    {draft.status === 'draft' && editingId !== draft.id && (
                      <button onClick={() => startEditing(draft)} style={{ background: 'transparent', border: 'none', color: '#00CFFF', fontSize: 11, fontWeight: 700, cursor: 'pointer' }}>✏️ Edit</button>
                    )}
                  </div>
                  
                  {editingId === draft.id ? (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 16, flex: 1 }}>
                      <input value={editData.headline} onChange={e => setEditData({...editData, headline: e.target.value})} style={{ background: '#000', border: '1px solid #333', color: '#fff', padding: '8px', borderRadius: 6, fontSize: 13, fontWeight: 700 }} />
                      <textarea value={editData.caption} onChange={e => setEditData({...editData, caption: e.target.value})} style={{ background: '#000', border: '1px solid #333', color: '#fff', padding: '8px', borderRadius: 6, fontSize: 12, flex: 1, resize: 'none' }} />
                      <div style={{ display: 'flex', gap: 10 }}>
                        <button onClick={() => saveEditing(draft.id)} style={{ flex: 1, background: '#00CFFF20', color: '#00CFFF', border: '1px solid #00CFFF50', padding: '6px', borderRadius: 6, fontWeight: 700, cursor: 'pointer' }}>Save</button>
                        <button onClick={() => setEditingId(null)} style={{ flex: 1, background: '#333', color: '#fff', border: 'none', padding: '6px', borderRadius: 6, fontWeight: 700, cursor: 'pointer' }}>Cancel</button>
                      </div>
                    </div>
                  ) : (
                    <>
                      <div style={{ fontSize: 14, fontWeight: 700, color: '#eee', marginBottom: 8 }}>{draft.headline}</div>
                      <div style={{ fontSize: 12, color: '#888', flex: 1, marginBottom: 16, display: '-webkit-box', WebkitLineClamp: 3, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>
                        {draft.caption}
                      </div>
                    </>
                  )}

                  {/* Actions */}
                  {draft.status === 'draft' && (
                    <div style={{ display: 'flex', gap: 10 }}>
                      <button onClick={() => handleApprove(draft.id)} style={{ flex: 1, padding: '10px', background: '#00FF8820', color: '#00FF88', border: '1px solid #00FF8850', borderRadius: 8, fontWeight: 700, cursor: 'pointer', transition: 'all 0.2s' }}>
                        ✓ Approve
                      </button>
                      <button onClick={() => handleReject(draft.id)} style={{ flex: 1, padding: '10px', background: '#FF325020', color: '#FF3250', border: '1px solid #FF325050', borderRadius: 8, fontWeight: 700, cursor: 'pointer', transition: 'all 0.2s' }}>
                        ✕ Reject
                      </button>
                    </div>
                  )}
                  {isApproved && (
                    <div style={{ textAlign: 'center', padding: '10px', background: '#00FF8810', color: '#00FF88', borderRadius: 8, fontSize: 12, fontWeight: 700 }}>
                      Will be published automatically
                    </div>
                  )}
                  {isRejected && (
                    <div style={{ textAlign: 'center', padding: '10px', background: '#FF325010', color: '#FF3250', borderRadius: 8, fontSize: 12, fontWeight: 700 }}>
                      Will be skipped
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
