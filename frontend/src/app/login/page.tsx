'use client';

import React, { useState, FormEvent } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/lib/auth-context';
import { Button, Input } from '@/components/ui';

export default function LoginPage() {
  const { login, loading, error } = useAuth();
  const router = useRouter();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [formError, setFormError] = useState<string | null>(null);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setFormError(null);
    try {
      await login(email, password);
      router.push('/dashboard');
    } catch (err: any) {
      setFormError(err.message || 'Login failed');
    }
  }

  return (
    <main className="auth-page">
      <div className="auth-card">
        <div className="auth-card__header">
          <h1 className="auth-card__title">Sign in</h1>
          <p className="auth-card__subtitle">Attention Profiling System</p>
        </div>

        <form onSubmit={handleSubmit} className="form-stack">
          <Input
            label="Email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            autoComplete="email"
          />
          <Input
            label="Password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            autoComplete="current-password"
            error={formError || undefined}
          />
          <Button type="submit" loading={loading} style={{ width: '100%' }}>
            Sign in
          </Button>
        </form>

        <p className="auth-card__footer">
          Don&apos;t have an account? <Link href="/register">Create one</Link>
        </p>
      </div>

      <style jsx>{`
        .auth-page {
          display: flex;
          justify-content: center;
          align-items: center;
          min-height: 100vh;
          padding: var(--space-4);
          background: var(--color-bg-secondary);
        }
        .auth-card {
          width: 100%;
          max-width: 360px;
          background: var(--color-bg-primary);
          border: var(--border-width) solid var(--color-border);
          border-radius: var(--radius-lg);
          padding: var(--space-8);
        }
        .auth-card__header {
          text-align: center;
          margin-bottom: var(--space-6);
        }
        .auth-card__title {
          font-size: var(--font-size-xl);
          margin-bottom: var(--space-1);
        }
        .auth-card__subtitle {
          font-size: var(--font-size-sm);
          color: var(--color-text-muted);
          margin-bottom: 0;
        }
        .auth-card__footer {
          text-align: center;
          margin-top: var(--space-4);
          font-size: var(--font-size-sm);
          color: var(--color-text-secondary);
          margin-bottom: 0;
        }
      `}</style>
    </main>
  );
}
