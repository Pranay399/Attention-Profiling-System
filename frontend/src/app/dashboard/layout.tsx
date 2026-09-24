'use client';

import React, { useEffect } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import Link from 'next/link';
import { useAuth } from '@/lib/auth-context';
import { LoadingSkeleton } from '@/components/ui';

/**
 * Dashboard layout — sidebar + content area.
 * Redirects to login if not authenticated.
 */
export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const { user, loading, logout } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    if (!loading && !user) {
      router.replace('/login');
    }
  }, [user, loading, router]);

  if (loading || !user) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '100vh' }}>
        <LoadingSkeleton lines={3} />
      </div>
    );
  }

  const initials = user.full_name
    .split(' ')
    .map((n) => n[0])
    .join('')
    .toUpperCase()
    .slice(0, 2);

  return (
    <div className="app-layout">
      <aside className="sidebar">
        <div className="sidebar__header">
          <div className="sidebar__brand">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="10" />
              <circle cx="12" cy="12" r="3" />
            </svg>
            APS
          </div>
        </div>

        <nav className="sidebar__nav">
          <div className="sidebar__section">
            <div className="sidebar__section-label">Navigation</div>
            <Link
              href="/dashboard"
              className={`sidebar__link ${pathname === '/dashboard' ? 'sidebar__link--active' : ''}`}
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <rect x="3" y="3" width="7" height="7" rx="1" />
                <rect x="14" y="3" width="7" height="7" rx="1" />
                <rect x="3" y="14" width="7" height="7" rx="1" />
                <rect x="14" y="14" width="7" height="7" rx="1" />
              </svg>
              Dashboard
            </Link>
            <Link
              href="/dashboard/live"
              className={`sidebar__link ${pathname === '/dashboard/live' ? 'sidebar__link--active' : ''}`}
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <polygon points="23 7 16 12 23 17 23 7"></polygon>
                <rect x="1" y="5" width="15" height="14" rx="2" ry="2"></rect>
              </svg>
              Live Classroom
            </Link>
          </div>
        </nav>

        <div className="sidebar__footer">
          <div className="sidebar__user">
            <span className="sidebar__avatar">{initials}</span>
            <span style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {user.full_name}
            </span>
            <button
              onClick={logout}
              className="btn btn--ghost btn--sm"
              style={{ padding: '2px 6px', fontSize: 'var(--font-size-xs)' }}
              aria-label="Sign out"
            >
              Sign out
            </button>
          </div>
        </div>
      </aside>

      <main className="app-content">
        {children}
      </main>
    </div>
  );
}
