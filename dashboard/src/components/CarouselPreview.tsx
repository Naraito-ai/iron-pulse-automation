'use client';

import React, { useState } from 'react';
import type { GeneratedPost } from '@/lib/api';

interface CarouselPreviewProps {
  posts: GeneratedPost[];
}

const ACCENT_COLORS = ['#00D4FF', '#8B5CF6', '#FF0080', '#FFC400', '#00FF88'];

function SlideThumb({
  url,
  idx,
  active,
  onClick,
}: {
  url: string;
  idx: number;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <div
      onClick={onClick}
      style={{
        aspectRatio: '1080/1350',
        background: 'var(--bg-surface)',
        borderRadius: 10,
        overflow: 'hidden',
        cursor: 'pointer',
        border: active ? '2px solid var(--accent-cyan)' : '2px solid transparent',
        transition: 'border-color 0.2s, transform 0.2s',
        transform: active ? 'scale(1.04)' : 'scale(1)',
        boxShadow: active ? 'var(--glow-cyan)' : 'none',
        flexShrink: 0,
        width: 80,
      }}
    >
      {url ? (
        <img src={`http://localhost:8000${url}`} alt={`Slide ${idx + 1}`}
          style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
      ) : (
        <div style={{
          width: '100%', height: '100%',
          display: 'flex', flexDirection: 'column',
          alignItems: 'center', justifyContent: 'center',
          gap: 4,
          background: `linear-gradient(135deg, rgba(0,212,255,0.06), rgba(139,92,246,0.06))`,
        }}>
          <span style={{ fontSize: 18 }}>🎨</span>
          <span style={{ fontSize: 9, color: 'var(--text-muted)' }}>Slide {idx + 1}</span>
        </div>
      )}
    </div>
  );
}

function PostPreview({ post, accent }: { post: GeneratedPost; accent: string }) {
  const [activeSlide, setActiveSlide] = useState(0);
  const slides = post.slide_paths || [];

  return (
    <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
      {/* Post header */}
      <div style={{
        padding: '16px 20px',
        borderBottom: '1px solid var(--border-subtle)',
        display: 'flex', alignItems: 'center', gap: 12,
      }}>
        <div style={{
          width: 36, height: 36, borderRadius: 10,
          background: `linear-gradient(135deg, ${accent}, rgba(139,92,246,0.8))`,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontWeight: 900, fontSize: 16, color: '#000',
          flexShrink: 0,
        }}>
          {post.rank}
        </div>
        <div style={{ minWidth: 0 }}>
          <div style={{
            fontFamily: 'var(--font-display)', fontWeight: 700, fontSize: 14,
            color: 'var(--text-primary)', overflow: 'hidden',
            textOverflow: 'ellipsis', whiteSpace: 'nowrap',
          }}>
            {post.headline}
          </div>
          <div style={{ fontSize: 11, color: 'var(--text-dim)', marginTop: 2 }}>
            {post.status} · {slides.length} slides
          </div>
        </div>
        <div className="status-pill" style={{ marginLeft: 'auto',
          ...(post.status === 'published' ? { background: 'rgba(0,255,136,0.1)', color: '#00FF88', border: '1px solid rgba(0,255,136,0.3)' } :
              post.status === 'generated' ? { background: 'rgba(0,212,255,0.1)', color: '#00D4FF', border: '1px solid rgba(0,212,255,0.3)' } :
              { background: 'rgba(255,196,0,0.1)', color: '#FFC400', border: '1px solid rgba(255,196,0,0.3)' }),
        }}>
          {post.status?.toUpperCase()}
        </div>
      </div>

      <div style={{ padding: 20 }}>
        {/* Main slide preview */}
        <div style={{
          aspectRatio: '1080/1350',
          background: 'var(--bg-surface)',
          borderRadius: 14,
          overflow: 'hidden',
          marginBottom: 14,
          position: 'relative',
          maxHeight: 280,
        }}>
          {slides[activeSlide] ? (
            <img
              src={`http://localhost:8000/images/generated/${slides[activeSlide].split(/[\\/]/).pop()}`}
              alt={`Slide ${activeSlide + 1}`}
              style={{ width: '100%', height: '100%', objectFit: 'cover' }}
              onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }}
            />
          ) : (
            <div style={{
              width: '100%', height: '100%', display: 'flex',
              flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 8,
              background: `linear-gradient(135deg, ${accent}10, rgba(139,92,246,0.08))`,
            }}>
              <span style={{ fontSize: 32 }}>🎨</span>
              <span style={{ fontSize: 11, color: 'var(--text-dim)' }}>Slide {activeSlide + 1}</span>
              <span style={{ fontSize: 10, color: 'var(--text-muted)', textAlign: 'center', maxWidth: 200, padding: '0 16px' }}>
                {post.headline}
              </span>
            </div>
          )}

          {/* Slide indicator */}
          <div style={{
            position: 'absolute', bottom: 10, left: '50%', transform: 'translateX(-50%)',
            display: 'flex', gap: 5,
          }}>
            {[0,1,2,3,4].map(i => (
              <div key={i} onClick={() => setActiveSlide(i)} style={{
                width: 6, height: 6, borderRadius: '50%', cursor: 'pointer',
                background: i === activeSlide ? accent : 'rgba(255,255,255,0.3)',
                transition: 'background 0.2s',
              }} />
            ))}
          </div>
        </div>

        {/* Slide thumbnails */}
        <div style={{ display: 'flex', gap: 8, overflowX: 'auto', paddingBottom: 4 }}>
          {[0,1,2,3,4].map(i => (
            <SlideThumb
              key={i} url={slides[i] ? `/images/generated/${slides[i].split(/[\\/]/).pop()}` : ''}
              idx={i} active={activeSlide === i} onClick={() => setActiveSlide(i)}
            />
          ))}
        </div>

        {/* Caption preview */}
        {post.caption && (
          <div style={{
            marginTop: 14, padding: '12px 14px',
            background: 'rgba(255,255,255,0.03)',
            borderRadius: 10, border: '1px solid var(--border-subtle)',
          }}>
            <div style={{ fontSize: 10, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.08em', fontWeight: 600, marginBottom: 6 }}>
              Caption Preview
            </div>
            <p style={{ fontSize: 12, color: 'var(--text-secondary)', lineHeight: 1.6,
              display: '-webkit-box', WebkitLineClamp: 3, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>
              {post.caption}
            </p>
          </div>
        )}

        {/* CTA */}
        {post.cta && (
          <div style={{
            marginTop: 10, padding: '8px 14px',
            background: `${accent}10`, borderRadius: 8,
            border: `1px solid ${accent}25`,
            fontSize: 12, color: accent, fontWeight: 600,
          }}>
            📣 {post.cta}
          </div>
        )}
      </div>
    </div>
  );
}

export default function CarouselPreview({ posts }: CarouselPreviewProps) {
  if (posts.length === 0) {
    return (
      <div style={{
        background: 'var(--bg-card)', borderRadius: 16, padding: 48,
        textAlign: 'center', border: '1px solid var(--border-subtle)',
      }}>
        <div style={{ fontSize: 48, marginBottom: 16 }}>🎨</div>
        <p style={{ color: 'var(--text-dim)', fontSize: 14 }}>
          No carousels generated yet. Run the pipeline to see slide previews.
        </p>
      </div>
    );
  }

  return (
    <div className="grid-3" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))' }}>
      {posts.map((post, i) => (
        <PostPreview key={post.id} post={post} accent={ACCENT_COLORS[i % ACCENT_COLORS.length]} />
      ))}
    </div>
  );
}
