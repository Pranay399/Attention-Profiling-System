'use client';

import React, { useState, FormEvent } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/lib/auth-context';
import { Button, Input } from '@/components/ui';

export default function RegisterPage() {
  const { register, loading } = useAuth();
  const router = useRouter();
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [role, setRole] = useState('teacher');
  const [formError, setFormError] = useState<string | null>(null);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setFormError(null);
    if (password.length < 8) {
      setFormError('Password must be at least 8 characters');
      return;
    }
    try {
      await register(email, password, fullName, role);
      router.push('/dashboard');
    } catch (err: any) {
      setFormError(err.message || 'Registration failed');
    }
  }

  return (
    <main className="auth-page">
      <div className="auth-card">
        <div className="auth-card__header">
          <h1 className="auth-card__title">Create account</h1>
          <p className="auth-card__subtitle">Attention Profiling System</p>
        </div>

        <form onSubmit={handleSubmit} className="form-stack">
          <Input
            label="Full name"
            type="text"
            value={fullName}
            onChange={(e) => setFullName(e.target.value)}
            required
            autoComplete="name"
          />
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
            autoComplete="new-password"
            description="At least 8 characters"
          />

          <div className="form-field">
            <label htmlFor="role" className="form-field__label">Role</label>
            <select
              id="role"
              className="form-field__input"
              value={role}
              onChange={(e) => setRole(e.target.value)}
            >
              <option value="teacher">Teacher</option>
              <option value="student">Student</option>
              <option value="administrator">Administrator</option>
            </select>
          </div>

          {formError && <p className="form-field__error" role="alert">{formError}</p>}

          <Button type="submit" loading={loading} style={{ width: '100%' }}>
            Create account
          </Button>
        </form>

        <p className="auth-card__footer">
          Already have an account? <Link href="/login">Sign in</Link>
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
