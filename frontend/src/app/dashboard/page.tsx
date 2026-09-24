'use client';

import React, { useEffect, useState, FormEvent } from 'react';
import Link from 'next/link';
import { useAuth } from '@/lib/auth-context';
import { courses as coursesApi, sessions as sessionsApi, Course, Session } from '@/lib/api';
import {
  Button, Input, Modal, PageHeader, EmptyState,
  ErrorState, LoadingSkeleton, StatusIndicator,
} from '@/components/ui';

/**
 * Dashboard page — shows the user's courses and recent sessions.
 */
export default function DashboardPage() {
  const { user } = useAuth();
  const [coursesList, setCourses] = useState<Course[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showCreateCourse, setShowCreateCourse] = useState(false);

  async function loadCourses() {
    try {
      setLoading(true);
      setError(null);
      const data = await coursesApi.list();
      setCourses(data);
    } catch (err: any) {
      setError(err.message || 'Failed to load courses');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadCourses();
  }, []);

  return (
    <div className="page-container">
      <PageHeader
        title="Dashboard"
        subtitle={`Welcome back, ${user?.full_name?.split(' ')[0] || 'User'}`}
        actions={
          (user?.role === 'teacher' || user?.role === 'administrator') && (
            <Button onClick={() => setShowCreateCourse(true)}>New course</Button>
          )
        }
      />

      {loading && <LoadingSkeleton lines={5} />}
      {error && <ErrorState message={error} onRetry={loadCourses} />}

      {!loading && !error && coursesList.length === 0 && (
        <EmptyState
          title="No courses yet"
          description="Create your first course to begin recording and analyzing classroom sessions."
          action={
            user?.role === 'teacher' && (
              <Button onClick={() => setShowCreateCourse(true)}>Create course</Button>
            )
          }
        />
      )}

      {!loading && !error && coursesList.length > 0 && (
        <div className="courses-list">
          {coursesList.map((course) => (
            <CourseCard key={course.id} course={course} />
          ))}
        </div>
      )}

      <CreateCourseModal
        open={showCreateCourse}
        onClose={() => setShowCreateCourse(false)}
        onCreated={() => {
          setShowCreateCourse(false);
          loadCourses();
        }}
      />

      <style jsx>{`
        .courses-list {
          display: flex;
          flex-direction: column;
          gap: var(--space-3);
        }
      `}</style>
    </div>
  );
}

function CourseCard({ course }: { course: Course }) {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [expanded, setExpanded] = useState(false);
  const [loading, setLoading] = useState(false);

  async function loadSessions() {
    if (sessions.length > 0) {
      setExpanded(!expanded);
      return;
    }
    setLoading(true);
    try {
      const data = await sessionsApi.list(course.id);
      setSessions(data);
      setExpanded(true);
    } catch {
      // Silently fail — user can retry
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="card">
      <div className="card__header" style={{ cursor: 'pointer' }} onClick={loadSessions}>
        <div>
          <span className="card__title">{course.name}</span>
          <span className="text-sm text-muted" style={{ marginLeft: 'var(--space-2)' }}>
            {course.code}
          </span>
        </div>
        <span className="text-sm text-muted">
          {loading ? 'Loading...' : expanded ? '▾' : '▸'}
        </span>
      </div>

      {expanded && (
        <div className="card__body" style={{ padding: 0 }}>
          {sessions.length === 0 ? (
            <div style={{ padding: 'var(--space-4)' }}>
              <EmptyState
                title="No sessions"
                description="Create a session to start recording lectures."
                action={
                  <Link href={`/dashboard/courses/${course.id}`}>
                    <Button variant="secondary" size="sm">Manage course</Button>
                  </Link>
                }
              />
            </div>
          ) : (
            <div>
              {sessions.slice(0, 5).map((session) => (
                <Link
                  key={session.id}
                  href={`/dashboard/sessions/${session.id}`}
                  className="session-item"
                  style={{ borderRadius: 0, borderLeft: 'none', borderRight: 'none', borderTop: 'none' }}
                >
                  <div className="session-item__info">
                    <span className="session-item__title">{session.title}</span>
                    <span className="session-item__meta">
                      {new Date(session.session_date).toLocaleDateString('en-US', {
                        month: 'short', day: 'numeric', year: 'numeric',
                      })}
                    </span>
                  </div>
                  <span className="text-sm text-muted">→</span>
                </Link>
              ))}
              {sessions.length > 5 && (
                <div style={{ padding: 'var(--space-2) var(--space-4)', textAlign: 'center' }}>
                  <Link href={`/dashboard/courses/${course.id}`} className="text-sm">
                    View all {sessions.length} sessions
                  </Link>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function CreateCourseModal({
  open, onClose, onCreated,
}: {
  open: boolean;
  onClose: () => void;
  onCreated: () => void;
}) {
  const [name, setName] = useState('');
  const [code, setCode] = useState('');
  const [description, setDescription] = useState('');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setSaving(true);
    setError(null);
    try {
      await coursesApi.create({ name, code, description: description || undefined });
      setName('');
      setCode('');
      setDescription('');
      onCreated();
    } catch (err: any) {
      setError(err.message || 'Failed to create course');
    } finally {
      setSaving(false);
    }
  }

  return (
    <Modal open={open} onClose={onClose} title="New course">
      <form onSubmit={handleSubmit} className="form-stack">
        <Input
          label="Course name"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="e.g., Data Structures"
          required
        />
        <Input
          label="Course code"
          value={code}
          onChange={(e) => setCode(e.target.value)}
          placeholder="e.g., CS201"
          required
          description="Must be unique"
        />
        <div className="form-field">
          <label htmlFor="course-desc" className="form-field__label">Description</label>
          <textarea
            id="course-desc"
            className="form-field__input"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            rows={3}
            style={{ resize: 'vertical' }}
          />
        </div>
        {error && <p className="form-field__error" role="alert">{error}</p>}
        <div className="form-actions">
          <Button type="button" variant="ghost" onClick={onClose}>Cancel</Button>
          <Button type="submit" loading={saving}>Create course</Button>
        </div>
      </form>
    </Modal>
  );
}
