'use client';

import React from 'react';
import {
  LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Legend,
} from 'recharts';
import type { AnalyticsSummary } from '@/lib/api';

interface AnalyticsChartProps {
  analytics: AnalyticsSummary;
}

const CUSTOM_TOOLTIP_STYLE = {
  background: 'var(--bg-card)',
  border: '1px solid var(--border-subtle)',
  borderRadius: 10,
  padding: '10px 14px',
  fontSize: 12,
  color: 'var(--text-secondary)',
};

function StatCard({ icon, label, value, color, sub }: {
  icon: string; label: string; value: string | number; color: string; sub?: string;
}) {
  return (
    <div className="card" style={{ padding: '18px 20px', position: 'relative', overflow: 'hidden' }}>
      <div style={{
        position: 'absolute', top: -20, right: -20, width: 80, height: 80,
        borderRadius: '50%',
        background: `radial-gradient(circle, ${color}15, transparent 70%)`,
      }} />
      <div style={{ fontSize: 22, marginBottom: 8 }}>{icon}</div>
      <div style={{ fontSize: 11, color: 'var(--text-dim)', textTransform: 'uppercase', letterSpacing: '0.08em', fontWeight: 600, marginBottom: 4 }}>
        {label}
      </div>
      <div style={{
        fontFamily: 'var(--font-display)', fontWeight: 800, fontSize: 28, color,
        lineHeight: 1,
      }}>
        {typeof value === 'number' ? value.toLocaleString() : value}
      </div>
      {sub && (
        <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4 }}>{sub}</div>
      )}
    </div>
  );
}

export default function AnalyticsChart({ analytics }: AnalyticsChartProps) {
  const snapshots = (analytics.snapshots || []).slice(-15);

  // Prepare chart data
  const chartData = snapshots.map((s, i) => ({
    name: `Post ${i + 1}`,
    likes: s.likes,
    shares: s.shares,
    saves: s.saves,
    reach: Math.round(s.reach / 100) * 100,
    engagement: parseFloat(s.engagement_rate.toFixed(2)),
    viral: parseFloat(s.viral_score.toFixed(2)),
  }));

  const hasDemoData = chartData.length > 0;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
      {/* KPI Stats */}
      <div className="grid-4">
        <StatCard icon="❤️" label="Total Likes"    value={analytics.total_likes}    color="#FF0080" />
        <StatCard icon="🔁" label="Total Shares"   value={analytics.total_shares}   color="#00D4FF" />
        <StatCard icon="🔖" label="Total Saves"    value={analytics.total_saves}    color="#FFC400" />
        <StatCard icon="👁️" label="Total Reach"    value={analytics.total_reach}    color="#8B5CF6" />
        <StatCard icon="💬" label="Comments"       value={analytics.total_comments} color="#00FF88" />
        <StatCard icon="📊" label="Avg Engagement" value={`${analytics.avg_engagement_rate}%`} color="#00D4FF"
          sub="Engagement rate" />
        <StatCard icon="⚡" label="Avg Viral Score" value={analytics.avg_viral_score.toFixed(1)} color="#FF0080"
          sub="Out of 10.0" />
        <StatCard icon="🏆" label="Best Viral"     value={analytics.best_viral_score.toFixed(1)} color="#FFC400"
          sub="Peak score" />
      </div>

      {hasDemoData ? (
        <div className="grid-2">
          {/* Engagement Line Chart */}
          <div className="chart-container">
            <div style={{ fontWeight: 700, fontSize: 14, marginBottom: 16, color: 'var(--text-primary)' }}>
              📈 Engagement & Viral Score
            </div>
            <ResponsiveContainer width="100%" height={220}>
              <LineChart data={chartData} margin={{ top: 5, right: 20, left: -10, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
                <XAxis dataKey="name" tick={{ fill: '#646E8C', fontSize: 11 }} />
                <YAxis tick={{ fill: '#646E8C', fontSize: 11 }} />
                <Tooltip contentStyle={CUSTOM_TOOLTIP_STYLE} />
                <Legend iconType="circle" wrapperStyle={{ fontSize: 11, color: '#646E8C' }} />
                <Line type="monotone" dataKey="engagement" stroke="#00D4FF" strokeWidth={2} dot={{ fill: '#00D4FF', r: 3 }} name="Engagement %" />
                <Line type="monotone" dataKey="viral" stroke="#FF0080" strokeWidth={2} dot={{ fill: '#FF0080', r: 3 }} name="Viral Score" />
              </LineChart>
            </ResponsiveContainer>
          </div>

          {/* Likes/Shares/Saves Bar Chart */}
          <div className="chart-container">
            <div style={{ fontWeight: 700, fontSize: 14, marginBottom: 16, color: 'var(--text-primary)' }}>
              📊 Likes · Shares · Saves
            </div>
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={chartData} margin={{ top: 5, right: 20, left: -10, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
                <XAxis dataKey="name" tick={{ fill: '#646E8C', fontSize: 11 }} />
                <YAxis tick={{ fill: '#646E8C', fontSize: 11 }} />
                <Tooltip contentStyle={CUSTOM_TOOLTIP_STYLE} />
                <Legend iconType="circle" wrapperStyle={{ fontSize: 11, color: '#646E8C' }} />
                <Bar dataKey="likes"  fill="#FF0080" radius={[4,4,0,0]} name="Likes" />
                <Bar dataKey="shares" fill="#00D4FF" radius={[4,4,0,0]} name="Shares" />
                <Bar dataKey="saves"  fill="#FFC400" radius={[4,4,0,0]} name="Saves" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      ) : (
        <div style={{
          background: 'var(--bg-card)', borderRadius: 16, padding: 48,
          textAlign: 'center', border: '1px solid var(--border-subtle)',
        }}>
          <div style={{ fontSize: 48, marginBottom: 16 }}>📊</div>
          <p style={{ color: 'var(--text-dim)', fontSize: 14 }}>
            Analytics data will appear after posts are published. Trigger the pipeline to start.
          </p>
        </div>
      )}
    </div>
  );
}
