'use client';

import React, { useEffect, useState } from 'react';
import type { SystemStatus } from '@/lib/api';

interface PostScheduleProps {
  status: SystemStatus | null;
}

function pad(n: number) { return n.toString().padStart(2, '0'); }

function Countdown({ seconds }: { seconds: number }) {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = seconds % 60;

  return (
    <div style={{ textAlign: 'center' }}>
      <div className="countdown-display">
        {pad(h)}<span style={{ opacity: 0.4, fontSize: 32 }}>:</span>
        {pad(m)}<span style={{ opacity: 0.4, fontSize: 32 }}>:</span>
        {pad(s)}
      </div>
      <div className="countdown-label">until next automated run</div>
    </div>
  );
}

export default function PostSchedule({ status }: PostScheduleProps) {
  const [countdown, setCountdown] = useState(status?.seconds_until_next || 0);

  useEffect(() => {
    setCountdown(status?.seconds_until_next || 0);
  }, [status]);

  useEffect(() => {
    const timer = setInterval(() => {
      setCountdown(prev => Math.max(0, prev - 1));
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  const nextRun = status?.next_run_at
    ? new Date(status.next_run_at).toLocaleString('en-US', {
        weekday: 'short', month: 'short', day: 'numeric',
        hour: '2-digit', minute: '2-digit', timeZoneName: 'short',
      })
    : 'Unknown';

  const lastRun = status?.last_run as Record<string, unknown> | null;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      {/* Countdown */}
      <div className="card" style={{ padding: 32 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 24, justifyContent: 'center' }}>
          <span style={{ fontSize: 16 }}>⏱️</span>
          <span style={{ fontSize: 12, color: 'var(--text-dim)', textTransform: 'uppercase', letterSpacing: '0.1em', fontWeight: 600 }}>
            Next Scheduled Run
          </span>
        </div>

        <Countdown seconds={countdown} />

        <div style={{
          marginTop: 24, padding: '10px 16px',
          background: 'rgba(0,212,255,0.06)',
          borderRadius: 10, border: '1px solid rgba(0,212,255,0.15)',
          textAlign: 'center', fontSize: 12, color: 'var(--text-secondary)',
        }}>
          🗓️ {nextRun}
        </div>
      </div>

      {/* Schedule Info */}
      <div className="card">
        <div style={{ fontSize: 13, fontWeight: 700, marginBottom: 16, color: 'var(--text-primary)' }}>
          ⚙️ Schedule Configuration
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {[
            { label: 'Daily Run Time', value: `${status?.schedule_time || '09:00'} IST`, icon: '🕘' },
            { label: 'Posts Per Day',  value: '5 carousel posts', icon: '📸' },
            { label: 'Slides Per Post', value: '5 slides', icon: '🎴' },
            { label: 'Analytics Refresh', value: 'Every 6 hours', icon: '📊' },
            { label: 'Mode', value: status?.demo_mode ? 'Demo Mode' : 'Live Mode', icon: status?.demo_mode ? '🔵' : '🟢' },
          ].map(({ label, value, icon }) => (
            <div key={label} style={{
              display: 'flex', justifyContent: 'space-between', alignItems: 'center',
              padding: '8px 0', borderBottom: '1px solid rgba(255,255,255,0.04)',
            }}>
              <span style={{ fontSize: 12, color: 'var(--text-dim)' }}>{icon} {label}</span>
              <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)' }}>{value}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Last Run Summary */}
      {lastRun && (
        <div className="card">
          <div style={{ fontSize: 13, fontWeight: 700, marginBottom: 16, color: 'var(--text-primary)' }}>
            🕐 Last Run
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {[
              { label: 'Date',       value: String(lastRun.run_date || '-') },
              { label: 'Status',     value: String(lastRun.status || '-') },
              { label: 'Published',  value: `${lastRun.posts_published || 0} / ${lastRun.posts_generated || 0} posts` },
              { label: 'Duration',   value: `${parseFloat(String(lastRun.duration_seconds || '0')).toFixed(1)}s` },
            ].map(({ label, value }) => (
              <div key={label} style={{
                display: 'flex', justifyContent: 'space-between',
                fontSize: 12, padding: '6px 0',
                borderBottom: '1px solid rgba(255,255,255,0.04)',
              }}>
                <span style={{ color: 'var(--text-dim)' }}>{label}</span>
                <span style={{
                  fontWeight: 600,
                  color: label === 'Status'
                    ? (value === 'completed' ? '#00FF88' : value === 'failed' ? '#ff3250' : '#FFC400')
                    : 'var(--text-secondary)',
                }}>
                  {value}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
