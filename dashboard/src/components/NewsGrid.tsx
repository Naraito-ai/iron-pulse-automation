'use client';

import React from 'react';
import type { NewsStory } from '@/lib/api';

interface NewsGridProps {
  stories: NewsStory[];
}

const SOURCE_COLORS: Record<string, string> = {
  'TechCrunch':       '#00D4FF',
  'The Verge':        '#8B5CF6',
  'WIRED':            '#FF0080',
  'VentureBeat':      '#FFC400',
  'MIT Technology Review': '#00FF88',
  'NewsAPI':          '#B4B9D2',
};

const RANK_GRADIENTS = [
  'linear-gradient(135deg, #00D4FF, #8B5CF6)',
  'linear-gradient(135deg, #8B5CF6, #FF0080)',
  'linear-gradient(135deg, #FF0080, #FFC400)',
  'linear-gradient(135deg, #FFC400, #00D4FF)',
  'linear-gradient(135deg, #00FF88, #00D4FF)',
];

function ViralityBar({ score }: { score: number }) {
  const pct = (score / 10) * 100;
  const color = score >= 8 ? '#00FF88' : score >= 6 ? '#FFC400' : '#00D4FF';
  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
        <span style={{ fontSize: 10, color: 'var(--text-dim)', textTransform: 'uppercase', letterSpacing: '0.08em', fontWeight: 600 }}>
          Virality Score
        </span>
        <span style={{ fontSize: 11, color, fontWeight: 700 }}>{score.toFixed(1)}</span>
      </div>
      <div className="virality-bar">
        <div
          className="virality-fill"
          style={{ width: `${pct}%`, background: color }}
        />
      </div>
    </div>
  );
}

function NewsCard({ story, index }: { story: NewsStory; index: number }) {
  const accent = SOURCE_COLORS[story.source] || '#00D4FF';
  const rankGradient = RANK_GRADIENTS[index % RANK_GRADIENTS.length];
  const keywords = (() => {
    try { return JSON.parse(story.keywords || '[]').slice(0, 3); }
    catch { return []; }
  })();

  return (
    <div className="news-card animate-fade-in-up" style={{ animationDelay: `${index * 0.1}s` }}>
      {/* Accent top border */}
      <div style={{
        position: 'absolute', top: 0, left: 0, right: 0, height: 2,
        background: rankGradient,
      }} />

      {/* Rank number */}
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 12 }}>
        <span
          className="news-rank"
          style={{ backgroundImage: rankGradient, WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent', backgroundClip: 'text' }}
        >
          #{story.rank}
        </span>
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 4 }}>
          <span
            className="news-source-chip"
            style={{
              background: `${accent}18`,
              color: accent,
              border: `1px solid ${accent}30`,
            }}
          >
            {story.source}
          </span>
          {story.published_at && (
            <span style={{ fontSize: 10, color: 'var(--text-muted)' }}>
              {new Date(story.published_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
            </span>
          )}
        </div>
      </div>

      {/* Title */}
      <h3 className="news-title">{story.title}</h3>

      {/* Summary */}
      {story.summary && (
        <p className="news-summary">{story.summary}</p>
      )}

      {/* Keywords */}
      {keywords.length > 0 && (
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4, margin: '10px 0' }}>
          {keywords.map((kw: string) => (
            <span key={kw} style={{
              fontSize: 10, padding: '2px 7px', borderRadius: 4,
              background: 'rgba(255,255,255,0.05)',
              color: 'var(--text-dim)',
              border: '1px solid rgba(255,255,255,0.06)',
            }}>
              {kw}
            </span>
          ))}
        </div>
      )}

      {/* Virality bar */}
      <ViralityBar score={story.virality_score} />
    </div>
  );
}

export default function NewsGrid({ stories }: NewsGridProps) {
  if (stories.length === 0) {
    return (
      <div style={{
        background: 'var(--bg-card)', borderRadius: 16, padding: 48,
        textAlign: 'center', border: '1px solid var(--border-subtle)',
      }}>
        <div style={{ fontSize: 48, marginBottom: 16 }}>📡</div>
        <p style={{ color: 'var(--text-dim)', fontSize: 14 }}>
          No stories fetched yet. Trigger the pipeline or wait for the 9:00 AM scheduled run.
        </p>
      </div>
    );
  }

  return (
    <div className="grid-5" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))' }}>
      {stories.map((story, i) => (
        <NewsCard key={story.id} story={story} index={i} />
      ))}
    </div>
  );
}
