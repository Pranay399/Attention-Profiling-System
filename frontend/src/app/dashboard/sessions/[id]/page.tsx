'use client';

import React, { useEffect, useState, useRef, useCallback } from 'react';
import Link from 'next/link';
import { useParams, useRouter } from 'next/navigation';
import {
  sessions as sessionsApi, recordings as recordingsApi,
  SessionDetail, Recording, AnalysisJob,
} from '@/lib/api';
import {
  Button, PageHeader, EmptyState, ErrorState,
  LoadingSkeleton, StatusIndicator, ProgressBar,
} from '@/components/ui';

export default function SessionPage() {
  const params = useParams();
  const sessionId = params.id as string;
  const router = useRouter();
  const [session, setSession] = useState<SessionDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState('');
  const [analyzing, setAnalyzing] = useState<string | null>(null); // recording ID being analyzed
  const [analysisJob, setAnalysisJob] = useState<AnalysisJob | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const load = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await sessionsApi.get(sessionId);
      setSession(data);
    } catch (err: any) {
      setError(err.message || 'Failed to load session');
    } finally {
      setLoading(false);
    }
  }, [sessionId]);

  useEffect(() => { load(); }, [load]);

  // Poll analysis job status
  useEffect(() => {
    if (!analysisJob || analysisJob.status === 'completed' || analysisJob.status === 'failed') return;

    const interval = setInterval(async () => {
      try {
        const { analysis } = await import('@/lib/api');
        const job = await analysis.get(analysisJob.id);
        setAnalysisJob(job);
        if (job.status === 'completed' || job.status === 'failed') {
          clearInterval(interval);
          load(); // Refresh session data
        }
      } catch {
        clearInterval(interval);
      }
    }, 2000);

    return () => clearInterval(interval);
  }, [analysisJob, load]);

  async function handleUpload(file: File) {
    setUploading(true);
    setUploadProgress(`Uploading ${file.name}...`);
    try {
      await recordingsApi.upload(sessionId, file);
      setUploadProgress('');
      await load();
    } catch (err: any) {
      setError(err.message || 'Upload failed');
    } finally {
      setUploading(false);
    }
  }

  async function handleAnalyze(recordingId: string) {
    setAnalyzing(recordingId);
    try {
      const job = await recordingsApi.analyze(recordingId);
      setAnalysisJob(job);
    } catch (err: any) {
      setError(err.message || 'Failed to start analysis');
    } finally {
      setAnalyzing(null);
    }
  }

  function handleDrop(e: React.DragEvent) {
    e.preventDefault();
    const file = e.dataTransfer.files[0];
    if (file) handleUpload(file);
  }

  if (loading) return <div className="page-container"><LoadingSkeleton lines={5} /></div>;
  if (error && !session) return <div className="page-container"><ErrorState message={error} onRetry={load} /></div>;
  if (!session) return <div className="page-container"><ErrorState message="Session not found" /></div>;

  const hasRecordings = session.recordings && session.recordings.length > 0;

  return (
    <div className="page-container">
      <PageHeader
        title={session.title}
        subtitle={new Date(session.session_date).toLocaleDateString('en-US', {
          weekday: 'long', month: 'long', day: 'numeric', year: 'numeric',
        })}
        breadcrumbs={[
          { label: 'Dashboard', href: '/dashboard' },
          { label: 'Session' },
        ]}
      />

      {session.description && (
        <p style={{ marginBottom: 'var(--space-4)', color: 'var(--color-text-secondary)', fontSize: 'var(--font-size-sm)' }}>
          {session.description}
        </p>
      )}

      {error && <ErrorState message={error} onRetry={load} />}

      {/* Upload area */}
      <div
        className={`upload-area ${uploading ? 'upload-area--active' : ''}`}
        onClick={() => fileInputRef.current?.click()}
        onDragOver={(e) => e.preventDefault()}
        onDrop={handleDrop}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') fileInputRef.current?.click(); }}
        aria-label="Upload recording"
      >
        <input
          ref={fileInputRef}
          type="file"
          accept=".mp4,.avi,.mov,.mkv,.webm"
          onChange={(e) => { const f = e.target.files?.[0]; if (f) handleUpload(f); }}
          style={{ display: 'none' }}
        />
        <p className="upload-area__label">
          {uploading ? uploadProgress : 'Drop a video file here or click to upload'}
        </p>
        <p className="upload-area__hint">
          Supported formats: MP4, AVI, MOV, MKV, WebM (max 500 MB)
        </p>
      </div>

      {/* Analysis progress */}
      {analysisJob && (analysisJob.status === 'queued' || analysisJob.status === 'processing') && (
        <div className="card" style={{ marginTop: 'var(--space-4)' }}>
          <div className="card__body">
            <div style={{ marginBottom: 'var(--space-2)' }}>
              <StatusIndicator status={analysisJob.status} />
            </div>
            {analysisJob.frames_total && analysisJob.frames_processed != null && (
              <ProgressBar
                value={analysisJob.frames_processed}
                max={analysisJob.frames_total}
                label="Analyzing frames"
              />
            )}
            <p className="text-sm text-muted" style={{ marginTop: 'var(--space-2)', marginBottom: 0 }}>
              Processing video with {analysisJob.model_version}...
            </p>
          </div>
        </div>
      )}

      {/* Recordings list */}
      {hasRecordings && (
        <div style={{ marginTop: 'var(--space-6)' }}>
          <h3 style={{ marginBottom: 'var(--space-3)' }}>Recordings</h3>
          <table className="data-table">
            <thead>
              <tr>
                <th>File</th>
                <th>Size</th>
                <th>Status</th>
                <th style={{ textAlign: 'right' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {session.recordings.map((rec) => (
                <RecordingRow
                  key={rec.id}
                  recording={rec}
                  onAnalyze={() => handleAnalyze(rec.id)}
                  analyzing={analyzing === rec.id}
                  analysisJob={analysisJob?.recording_id === rec.id ? analysisJob : null}
                />
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function RecordingRow({
  recording, onAnalyze, analyzing, analysisJob,
}: {
  recording: Recording;
  onAnalyze: () => void;
  analyzing: boolean;
  analysisJob: AnalysisJob | null;
}) {
  const router = useRouter();
  const fileSize = recording.file_size_bytes
    ? `${(recording.file_size_bytes / (1024 * 1024)).toFixed(1)} MB`
    : '—';

  const canAnalyze = recording.status === 'uploaded' || recording.status === 'completed';
  const hasCompleteAnalysis = analysisJob?.status === 'completed';

  return (
    <tr>
      <td>
        <span className="font-medium">{recording.filename}</span>
      </td>
      <td className="num">{fileSize}</td>
      <td><StatusIndicator status={recording.status} /></td>
      <td style={{ textAlign: 'right' }}>
        <div style={{ display: 'flex', gap: 'var(--space-2)', justifyContent: 'flex-end' }}>
          {hasCompleteAnalysis && (
            <Link href={`/dashboard/analysis/${analysisJob!.id}`}>
              <Button variant="secondary" size="sm">View results</Button>
            </Link>
          )}
          {canAnalyze && (
            <Button
              size="sm"
              onClick={onAnalyze}
              loading={analyzing}
              disabled={analyzing}
            >
              {analyzing ? 'Starting...' : 'Analyze'}
            </Button>
          )}
        </div>
      </td>
    </tr>
  );
}
