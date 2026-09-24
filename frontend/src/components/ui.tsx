/**
 * Shared UI components.
 *
 * Each component is small, focused, and uses design tokens.
 * No unnecessary abstraction — these are the building blocks
 * that appear across multiple pages.
 */

'use client';

import React, { forwardRef, ButtonHTMLAttributes, InputHTMLAttributes, ReactNode } from 'react';

// ── Button ──────────────────────────────────────────────────────────────

type ButtonVariant = 'primary' | 'secondary' | 'ghost' | 'danger';
type ButtonSize = 'sm' | 'md';

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  loading?: boolean;
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ variant = 'primary', size = 'md', loading, children, disabled, className = '', ...props }, ref) => {
    return (
      <button
        ref={ref}
        className={`btn btn--${variant} btn--${size} ${loading ? 'btn--loading' : ''} ${className}`}
        disabled={disabled || loading}
        {...props}
      >
        {loading && <span className="btn__spinner" aria-hidden="true" />}
        <span className={loading ? 'btn__content--hidden' : ''}>{children}</span>
      </button>
    );
  }
);
Button.displayName = 'Button';

// ── Input ───────────────────────────────────────────────────────────────

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label: string;
  error?: string;
  description?: string;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ label, error, description, id, className = '', ...props }, ref) => {
    const inputId = id || label.toLowerCase().replace(/\s+/g, '-');
    const descId = description ? `${inputId}-desc` : undefined;
    const errorId = error ? `${inputId}-error` : undefined;

    return (
      <div className={`form-field ${error ? 'form-field--error' : ''} ${className}`}>
        <label htmlFor={inputId} className="form-field__label">
          {label}
        </label>
        {description && (
          <p id={descId} className="form-field__description">
            {description}
          </p>
        )}
        <input
          ref={ref}
          id={inputId}
          className="form-field__input"
          aria-describedby={[descId, errorId].filter(Boolean).join(' ') || undefined}
          aria-invalid={!!error}
          {...props}
        />
        {error && (
          <p id={errorId} className="form-field__error" role="alert">
            {error}
          </p>
        )}
      </div>
    );
  }
);
Input.displayName = 'Input';

// ── Badge ───────────────────────────────────────────────────────────────

type BadgeVariant = 'default' | 'success' | 'warning' | 'danger' | 'neutral';

interface BadgeProps {
  variant?: BadgeVariant;
  children: ReactNode;
}

export function Badge({ variant = 'default', children }: BadgeProps) {
  return <span className={`badge badge--${variant}`}>{children}</span>;
}

// ── StatusIndicator ─────────────────────────────────────────────────────

interface StatusIndicatorProps {
  status: string;
  label?: string;
}

const STATUS_MAP: Record<string, { variant: BadgeVariant; label: string }> = {
  uploaded: { variant: 'neutral', label: 'Uploaded' },
  queued: { variant: 'neutral', label: 'Queued' },
  processing: { variant: 'warning', label: 'Processing' },
  completed: { variant: 'success', label: 'Completed' },
  failed: { variant: 'danger', label: 'Failed' },
};

export function StatusIndicator({ status, label }: StatusIndicatorProps) {
  const config = STATUS_MAP[status] || { variant: 'default' as BadgeVariant, label: status };
  return (
    <span className={`status-indicator status-indicator--${config.variant}`}>
      <span className="status-indicator__dot" aria-hidden="true" />
      <span>{label || config.label}</span>
    </span>
  );
}

// ── BehaviorBadge ───────────────────────────────────────────────────────

const BEHAVIOR_MAP: Record<string, { label: string; className: string }> = {
  attentive: { label: 'Attentive', className: 'behavior--attentive' },
  looking_away: { label: 'Looking away', className: 'behavior--looking-away' },
  head_down: { label: 'Head down', className: 'behavior--head-down' },
  not_visible: { label: 'Not visible', className: 'behavior--not-visible' },
};

export function BehaviorBadge({ behavior }: { behavior: string }) {
  const config = BEHAVIOR_MAP[behavior] || { label: behavior, className: '' };
  return <span className={`behavior-badge ${config.className}`}>{config.label}</span>;
}

// ── ProgressBar ─────────────────────────────────────────────────────────

interface ProgressBarProps {
  value: number;
  max: number;
  label?: string;
}

export function ProgressBar({ value, max, label }: ProgressBarProps) {
  const percentage = max > 0 ? Math.round((value / max) * 100) : 0;
  return (
    <div className="progress">
      {label && <span className="progress__label">{label}</span>}
      <div className="progress__track" role="progressbar" aria-valuenow={value} aria-valuemin={0} aria-valuemax={max}>
        <div className="progress__fill" style={{ width: `${percentage}%` }} />
      </div>
      <span className="progress__text">{percentage}%</span>
    </div>
  );
}

// ── EmptyState ──────────────────────────────────────────────────────────

interface EmptyStateProps {
  title: string;
  description?: string;
  action?: ReactNode;
}

export function EmptyState({ title, description, action }: EmptyStateProps) {
  return (
    <div className="empty-state">
      <h3 className="empty-state__title">{title}</h3>
      {description && <p className="empty-state__description">{description}</p>}
      {action && <div className="empty-state__action">{action}</div>}
    </div>
  );
}

// ── ErrorState ──────────────────────────────────────────────────────────

interface ErrorStateProps {
  message?: string;
  onRetry?: () => void;
}

export function ErrorState({ message = 'Something went wrong.', onRetry }: ErrorStateProps) {
  return (
    <div className="error-state" role="alert">
      <p className="error-state__message">{message}</p>
      {onRetry && (
        <Button variant="secondary" size="sm" onClick={onRetry}>
          Retry
        </Button>
      )}
    </div>
  );
}

// ── LoadingSkeleton ─────────────────────────────────────────────────────

export function LoadingSkeleton({ lines = 3 }: { lines?: number }) {
  return (
    <div className="skeleton" aria-busy="true" aria-label="Loading content">
      {Array.from({ length: lines }, (_, i) => (
        <div key={i} className="skeleton__line" style={{ width: `${80 - i * 15}%` }} />
      ))}
    </div>
  );
}

// ── PageHeader ──────────────────────────────────────────────────────────

interface PageHeaderProps {
  title: string;
  subtitle?: string;
  breadcrumbs?: { label: string; href?: string }[];
  actions?: ReactNode;
}

export function PageHeader({ title, subtitle, breadcrumbs, actions }: PageHeaderProps) {
  return (
    <header className="page-header">
      {breadcrumbs && breadcrumbs.length > 0 && (
        <nav className="page-header__breadcrumbs" aria-label="Breadcrumb">
          <ol>
            {breadcrumbs.map((crumb, i) => (
              <li key={i}>
                {crumb.href ? <a href={crumb.href}>{crumb.label}</a> : <span>{crumb.label}</span>}
                {i < breadcrumbs.length - 1 && <span className="page-header__separator" aria-hidden="true">/</span>}
              </li>
            ))}
          </ol>
        </nav>
      )}
      <div className="page-header__row">
        <div>
          <h1 className="page-header__title">{title}</h1>
          {subtitle && <p className="page-header__subtitle">{subtitle}</p>}
        </div>
        {actions && <div className="page-header__actions">{actions}</div>}
      </div>
    </header>
  );
}

// ── Modal ────────────────────────────────────────────────────────────────

interface ModalProps {
  open: boolean;
  onClose: () => void;
  title: string;
  children: ReactNode;
}

export function Modal({ open, onClose, title, children }: ModalProps) {
  const dialogRef = React.useRef<HTMLDialogElement>(null);

  React.useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;

    if (open && !dialog.open) {
      dialog.showModal();
    } else if (!open && dialog.open) {
      dialog.close();
    }
  }, [open]);

  return (
    <dialog
      ref={dialogRef}
      className="modal"
      onClose={onClose}
      onClick={(e) => {
        // Close on backdrop click
        if (e.target === dialogRef.current) onClose();
      }}
    >
      <div className="modal__content">
        <div className="modal__header">
          <h2 className="modal__title">{title}</h2>
          <button className="modal__close" onClick={onClose} aria-label="Close dialog">
            ✕
          </button>
        </div>
        <div className="modal__body">{children}</div>
      </div>
    </dialog>
  );
}
