'use client';

import React, { useEffect, useRef, useState } from 'react';
import type { LogEntry } from '@/lib/api';
import { WS_URL } from '@/lib/api';

interface WsMessage {
  type: string;
  level?: string;
  module?: string;
  message?: string;
  timestamp?: string;
  [key: string]: unknown;
}

interface AutomationLogProps {
  initialLogs: LogEntry[];
}

const LEVEL_CLASS: Record<string, string> = {
  INFO:    'log-info',
  SUCCESS: 'log-success',
  WARNING: 'log-warning',
  ERROR:   'log-error',
};

const LEVEL_ICON: Record<string, string> = {
  INFO:    '●',
  SUCCESS: '✓',
  WARNING: '⚠',
  ERROR:   '✕',
};

function formatTime(iso: string) {
  try {
    const d = new Date(iso);
    return d.toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' });
  } catch { return iso.slice(11, 19); }
}

export default function AutomationLog({ initialLogs }: AutomationLogProps) {
  const [logs, setLogs] = useState<LogEntry[]>(initialLogs);
  const [wsStatus, setWsStatus] = useState<'connecting' | 'live' | 'offline'>('connecting');
  const feedRef = useRef<HTMLDivElement>(null);
  const wsRef   = useRef<WebSocket | null>(null);

  // Auto-scroll to bottom
  useEffect(() => {
    if (feedRef.current) {
      feedRef.current.scrollTop = feedRef.current.scrollHeight;
    }
  }, [logs]);

  // WebSocket connection
  useEffect(() => {
    function connect() {
      try {
        const ws = new WebSocket(WS_URL);
        wsRef.current = ws;

        ws.onopen = () => setWsStatus('live');
        ws.onclose = () => {
          setWsStatus('offline');
          setTimeout(connect, 3000);
        };
        ws.onerror = () => setWsStatus('offline');

        ws.onmessage = (evt) => {
          try {
            const data: WsMessage = JSON.parse(evt.data);
            if (data.type === 'log' && data.message) {
              const fakeEntry: LogEntry = {
                id: Date.now(),
                run_date: new Date().toISOString().slice(0, 10),
                level: data.level || 'INFO',
                module: data.module || 'System',
                message: data.message,
                details: '',
                created_at: data.timestamp || new Date().toISOString(),
              };
              setLogs(prev => [...prev.slice(-199), fakeEntry]);
            }
          } catch { /* ignore parse errors */ }
        };
      } catch {
        setWsStatus('offline');
        setTimeout(connect, 3000);
      }
    }

    connect();
    return () => wsRef.current?.close();
  }, []);

  return (
    <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
      {/* Header */}
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '16px 20px', borderBottom: '1px solid var(--border-subtle)',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{ fontSize: 16 }}>📋</span>
          <span style={{ fontWeight: 700, fontSize: 15 }}>Automation Log</span>
        </div>
        <div className={`status-pill ${wsStatus === 'live' ? 'status-live' : wsStatus === 'connecting' ? 'status-pending' : 'status-error'}`}>
          <span className="pulse-dot" />
          {wsStatus === 'live' ? 'LIVE' : wsStatus === 'connecting' ? 'CONNECTING' : 'OFFLINE'}
        </div>
      </div>

      {/* Log entries */}
      <div ref={feedRef} className="log-feed" style={{ borderRadius: 0, border: 'none', height: 380 }}>
        {logs.length === 0 && (
          <div style={{ color: 'var(--text-muted)', textAlign: 'center', paddingTop: 40 }}>
            No logs yet. Trigger the pipeline to see activity.
          </div>
        )}
        {[...logs].reverse().map((entry) => {
          const cls = LEVEL_CLASS[entry.level] || 'log-info';
          const icon = LEVEL_ICON[entry.level] || '●';
          return (
            <div key={entry.id} className={`log-entry ${cls}`}>
              <span className="log-time">{formatTime(entry.created_at)}</span>
              <span className="log-module">{icon} {entry.module}</span>
              <span className="log-msg">{entry.message}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
