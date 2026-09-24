'use client';

import React, { useEffect, useState, useMemo } from 'react';
import { useParams } from 'next/navigation';
import {
  analysis as analysisApi,
  AnalysisJob, AnalysisSummary, TimelineBucket,
} from '@/lib/api';
import {
  PageHeader, ErrorState, LoadingSkeleton,
  StatusIndicator, BehaviorBadge,
} from '@/components/ui';
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Cell,
} from 'recharts';

/**
 * Analysis results page.
 *
 * Displays:
 * 1. Session summary statistics
 * 2. Behavior timeline (stacked horizontal bars per participant)
 * 3. Overall behavior distribution (horizontal bar chart)
 * 4. Per-participant breakdown table
 */
export default function AnalysisPage() {
  const params = useParams();
  const analysisId = params.id as string;

  const [job, setJob] = useState<AnalysisJob | null>(null);
  const [summary, setSummary] = useState<AnalysisSummary | null>(null);
  const [timeline, setTimeline] = useState<TimelineBucket[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    try {
      setLoading(true);
      setError(null);
      const [jobData, summaryData, timelineData] = await Promise.all([
        analysisApi.get(analysisId),
        analysisApi.summary(analysisId),
        analysisApi.timeline(analysisId),
      ]);
      setJob(jobData);
      setSummary(summaryData);
      setTimeline(timelineData);
    } catch (err: any) {
      setError(err.message || 'Failed to load analysis results');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, [analysisId]);

  if (loading) return <div className="page-container"><LoadingSkeleton lines={8} /></div>;
  if (error) return <div className="page-container"><ErrorState message={error} onRetry={load} /></div>;
  if (!job || !summary) return <div className="page-container"><ErrorState message="Analysis not found" /></div>;

  return (
    <div className="page-container">
      <PageHeader
        title="Analysis Results"
        subtitle={`${summary.total_participants} participant${summary.total_participants !== 1 ? 's' : ''} • ${summary.total_observations} observations${summary.duration_seconds ? ` • ${formatDuration(summary.duration_seconds)}` : ''}`}
        breadcrumbs={[
          { label: 'Dashboard', href: '/dashboard' },
          { label: 'Analysis Results' },
        ]}
      />

      {/* Summary stats */}
      <div className="stats-row">
        <div className="stat">
          <span className="stat__label">Status</span>
          <StatusIndicator status={job.status} />
        </div>
        <div className="stat">
          <span className="stat__label">Participants</span>
          <span className="stat__value">{summary.total_participants}</span>
        </div>
        <div className="stat">
          <span className="stat__label">Frames</span>
          <span className="stat__value">{job.frames_processed || 0}</span>
        </div>
        <div className="stat">
          <span className="stat__label">Model</span>
          <span className="text-sm mono">{job.model_version}</span>
        </div>
      </div>

      {/* Behavior timeline */}
      {timeline.length > 0 && (
        <section style={{ marginBottom: 'var(--space-6)' }}>
          <h3 style={{ marginBottom: 'var(--space-3)' }}>Behavior Timeline</h3>
          <BehaviorTimeline timeline={timeline} duration={summary.duration_seconds} />
          <BehaviorLegend />
        </section>
      )}

      {/* Two-column layout: distribution + summary */}
      <div className="grid-2" style={{ marginBottom: 'var(--space-6)' }}>
        {/* Behavior distribution chart */}
        <div className="card">
          <div className="card__header">
            <span className="card__title">Behavior Distribution</span>
          </div>
          <div className="card__body">
            <BehaviorDistribution distribution={summary.overall_behavior_distribution} />
          </div>
        </div>

        {/* Session overview */}
        <div className="card">
          <div className="card__header">
            <span className="card__title">Session Overview</span>
          </div>
          <div className="card__body">
            {summary.overall_behavior_distribution.map((item) => (
              <div key={item.behavior} style={{ display: 'flex', justifyContent: 'space-between', padding: 'var(--space-1) 0' }}>
                <BehaviorBadge behavior={item.behavior} />
                <span className="text-sm mono">{item.percentage}%</span>
              </div>
            ))}
            {summary.duration_seconds && (
              <div style={{ marginTop: 'var(--space-3)', paddingTop: 'var(--space-3)', borderTop: 'var(--border-width) solid var(--color-border-subtle)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span className="text-sm text-muted">Duration</span>
                  <span className="text-sm mono">{formatDuration(summary.duration_seconds)}</span>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Participant table */}
      <section>
        <h3 style={{ marginBottom: 'var(--space-3)' }}>Participants</h3>
        <ParticipantTable participants={summary.participant_summaries} />
      </section>
    </div>
  );
}

// ── Sub-components ──────────────────────────────────────────────────────

function BehaviorTimeline({
  timeline,
  duration,
}: {
  timeline: TimelineBucket[];
  duration: number | null;
}) {
  // Group by participant
  const participants = useMemo(() => {
    const grouped: Record<string, { label: string; buckets: TimelineBucket[] }> = {};
    for (const bucket of timeline) {
      if (!grouped[bucket.participant_id]) {
        grouped[bucket.participant_id] = { label: bucket.label, buckets: [] };
      }
      grouped[bucket.participant_id].buckets.push(bucket);
    }
    return Object.entries(grouped);
  }, [timeline]);

  const maxTime = duration || Math.max(...timeline.map((t) => t.timestamp_sec + 5));

  return (
    <div className="timeline-chart" style={{ marginBottom: 'var(--space-3)' }}>
      {participants.map(([pid, { label, buckets }]) => (
        <div key={pid} className="timeline-row">
          <span className="timeline-row__label">{label}</span>
          <div className="timeline-row__blocks">
            {buckets.map((bucket, i) => {
              const width = (5 / maxTime) * 100; // each bucket is 5 seconds
              const left = (bucket.timestamp_sec / maxTime) * 100;
              return (
                <div
                  key={i}
                  className="timeline-block"
                  style={{
                    position: 'absolute',
                    left: `${left}%`,
                    width: `${Math.max(width, 0.5)}%`,
                    background: getBehaviorColor(bucket.behavior),
                  }}
                  title={`${label} — ${bucket.behavior.replace('_', ' ')} at ${formatTime(bucket.timestamp_sec)}`}
                />
              );
            })}
          </div>
        </div>
      ))}
      {/* Time axis */}
      <div className="timeline-row" style={{ marginTop: 'var(--space-1)' }}>
        <span className="timeline-row__label" />
        <div style={{ flex: 1, display: 'flex', justifyContent: 'space-between' }}>
          <span className="text-xs text-muted">0:00</span>
          {maxTime > 60 && <span className="text-xs text-muted">{formatTime(maxTime / 2)}</span>}
          <span className="text-xs text-muted">{formatTime(maxTime)}</span>
        </div>
      </div>

      <style jsx>{`
        .timeline-row__blocks {
          position: relative;
        }
      `}</style>
    </div>
  );
}

function BehaviorDistribution({ distribution }: { distribution: { behavior: string; count: number; percentage: number }[] }) {
  const data = distribution.map((d) => ({
    name: d.behavior.replace('_', ' '),
    value: d.percentage,
    behavior: d.behavior,
  }));

  return (
    <div className="bar-chart">
      {data.map((item) => (
        <div key={item.behavior} className="bar-chart__row">
          <span className="bar-chart__label">{item.name}</span>
          <div className="bar-chart__track">
            <div
              className="bar-chart__fill"
              style={{
                width: `${item.value}%`,
                background: getBehaviorColor(item.behavior),
              }}
            />
          </div>
          <span className="bar-chart__value">{item.value}%</span>
        </div>
      ))}
    </div>
  );
}

function ParticipantTable({ participants }: { participants: AnalysisSummary['participant_summaries'] }) {
  if (participants.length === 0) {
    return <p className="text-sm text-muted">No participants detected.</p>;
  }

  function getPercentage(p: typeof participants[0], behavior: string): string {
    const item = p.behavior_breakdown.find((b) => b.behavior === behavior);
    return item ? `${item.percentage}%` : '—';
  }

  return (
    <table className="data-table">
      <thead>
        <tr>
          <th>Participant</th>
          <th className="num">Observations</th>
          <th className="num">Attentive</th>
          <th className="num">Looking away</th>
          <th className="num">Head down</th>
          <th className="num">Confidence</th>
        </tr>
      </thead>
      <tbody>
        {participants.map((p) => (
          <tr key={p.participant_id}>
            <td><span className="font-medium">{p.label}</span></td>
            <td className="num">{p.total_observations}</td>
            <td className="num">{getPercentage(p, 'attentive')}</td>
            <td className="num">{getPercentage(p, 'looking_away')}</td>
            <td className="num">{getPercentage(p, 'head_down')}</td>
            <td className="num">{p.avg_confidence != null ? p.avg_confidence.toFixed(2) : '—'}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function BehaviorLegend() {
  const items = [
    { behavior: 'attentive', label: 'Attentive' },
    { behavior: 'looking_away', label: 'Looking away' },
    { behavior: 'head_down', label: 'Head down' },
    { behavior: 'not_visible', label: 'Not visible' },
  ];

  return (
    <div className="behavior-legend">
      {items.map((item) => (
        <div key={item.behavior} className="behavior-legend__item">
          <span
            className="behavior-legend__swatch"
            style={{ background: getBehaviorColor(item.behavior) }}
          />
          <span>{item.label}</span>
        </div>
      ))}
    </div>
  );
}

// ── Utilities ───────────────────────────────────────────────────────────

function getBehaviorColor(behavior: string): string {
  const colors: Record<string, string> = {
    attentive: 'var(--behavior-attentive)',
    looking_away: 'var(--behavior-looking-away)',
    head_down: 'var(--behavior-head-down)',
    not_visible: 'var(--behavior-not-visible)',
  };
  return colors[behavior] || 'var(--color-neutral)';
}

function formatDuration(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${s.toString().padStart(2, '0')}`;
}

function formatTime(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${s.toString().padStart(2, '0')}`;
}
