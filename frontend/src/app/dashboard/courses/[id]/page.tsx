'use client';

import React, { useEffect, useState, FormEvent } from 'react';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import { useAuth } from '@/lib/auth-context';
import {
  courses as coursesApi, sessions as sessionsApi,
  CourseDetail, Session,
} from '@/lib/api';
import {
  Button, Input, Modal, PageHeader, EmptyState,
  ErrorState, LoadingSkeleton,
} from '@/components/ui';

export default function CoursePage() {
  const params = useParams();
  const courseId = params.id as string;
  const { user } = useAuth();
  const [course, setCourse] = useState<CourseDetail | null>(null);
  const [sessionsList, setSessions] = useState<Session[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showCreateSession, setShowCreateSession] = useState(false);

  async function load() {
    try {
      setLoading(true);
      setError(null);
      const [courseData, sessionsData] = await Promise.all([
        coursesApi.get(courseId),
        sessionsApi.list(courseId),
      ]);
      setCourse(courseData);
      setSessions(sessionsData);
    } catch (err: any) {
      setError(err.message || 'Failed to load course');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, [courseId]);

  if (loading) return <div className="page-container"><LoadingSkeleton lines={5} /></div>;
  if (error) return <div className="page-container"><ErrorState message={error} onRetry={load} /></div>;
  if (!course) return <div className="page-container"><ErrorState message="Course not found" /></div>;

  return (
    <div className="page-container">
      <PageHeader
        title={course.name}
        subtitle={`${course.code} • ${course.session_count} session${course.session_count !== 1 ? 's' : ''}`}
        breadcrumbs={[
          { label: 'Dashboard', href: '/dashboard' },
          { label: course.name },
        ]}
        actions={<Button onClick={() => setShowCreateSession(true)}>New session</Button>}
      />

      {sessionsList.length === 0 ? (
        <EmptyState
          title="No sessions yet"
          description="Create a session for each class meeting. You can then upload recordings for analysis."
          action={<Button onClick={() => setShowCreateSession(true)}>Create session</Button>}
        />
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
          {sessionsList.map((session) => (
            <Link
              key={session.id}
              href={`/dashboard/sessions/${session.id}`}
              className="session-item"
            >
              <div className="session-item__info">
                <span className="session-item__title">{session.title}</span>
                <span className="session-item__meta">
                  {new Date(session.session_date).toLocaleDateString('en-US', {
                    weekday: 'short', month: 'short', day: 'numeric', year: 'numeric',
                  })}
                </span>
              </div>
              <span className="text-sm text-muted">→</span>
            </Link>
          ))}
        </div>
      )}

      <CreateSessionModal
        open={showCreateSession}
        courseId={courseId}
        onClose={() => setShowCreateSession(false)}
        onCreated={() => {
          setShowCreateSession(false);
          load();
        }}
      />
    </div>
  );
}

function CreateSessionModal({
  open, courseId, onClose, onCreated,
}: {
  open: boolean;
  courseId: string;
  onClose: () => void;
  onCreated: () => void;
}) {
  const [title, setTitle] = useState('');
  const [date, setDate] = useState(new Date().toISOString().slice(0, 10));
  const [description, setDescription] = useState('');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setSaving(true);
    setError(null);
    try {
      await sessionsApi.create(courseId, {
        title,
        session_date: date,
        description: description || undefined,
      });
      setTitle('');
      setDescription('');
      onCreated();
    } catch (err: any) {
      setError(err.message || 'Failed to create session');
    } finally {
      setSaving(false);
    }
  }

  return (
    <Modal open={open} onClose={onClose} title="New session">
      <form onSubmit={handleSubmit} className="form-stack">
        <Input label="Title" value={title} onChange={(e) => setTitle(e.target.value)} required placeholder="e.g., Lecture 14 — Binary Trees" />
        <Input label="Date" type="date" value={date} onChange={(e) => setDate(e.target.value)} required />
        <div className="form-field">
          <label htmlFor="session-desc" className="form-field__label">Description</label>
          <textarea id="session-desc" className="form-field__input" value={description} onChange={(e) => setDescription(e.target.value)} rows={2} style={{ resize: 'vertical' }} />
        </div>
        {error && <p className="form-field__error" role="alert">{error}</p>}
        <div className="form-actions">
          <Button type="button" variant="ghost" onClick={onClose}>Cancel</Button>
          <Button type="submit" loading={saving}>Create session</Button>
        </div>
      </form>
    </Modal>
  );
}
