'use client';

import type {
  ButtonHTMLAttributes,
  InputHTMLAttributes,
  ReactNode,
  SelectHTMLAttributes,
  TextareaHTMLAttributes,
} from 'react';

/* ------------------------------------------------------------------ */
/* Button                                                              */
/* ------------------------------------------------------------------ */

type ButtonVariant = 'primary' | 'secondary' | 'ghost' | 'danger' | 'outline';

const BUTTON_VARIANTS: Record<ButtonVariant, string> = {
  primary: 'bg-acid text-black font-medium hover:bg-acid-dim disabled:opacity-50 disabled:cursor-not-allowed',
  secondary: 'bg-off-black text-off-white hover:bg-border disabled:opacity-50 disabled:cursor-not-allowed',
  outline: 'border border-border text-off-white hover:border-acid/60 hover:text-acid disabled:opacity-50 disabled:cursor-not-allowed',
  ghost: 'text-muted hover:text-off-white hover:bg-off-black disabled:opacity-50 disabled:cursor-not-allowed',
  danger: 'bg-red-950/60 text-red-300 border border-red-900/60 hover:bg-red-900/40 disabled:opacity-50 disabled:cursor-not-allowed',
};

export function Button({
  variant = 'primary',
  className = '',
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: ButtonVariant }) {
  return (
    <button
      className={`inline-flex items-center justify-center gap-2 rounded-lg px-4 py-2 text-sm transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-acid/60 ${BUTTON_VARIANTS[variant]} ${className}`}
      {...props}
    />
  );
}

/* ------------------------------------------------------------------ */
/* Card                                                                */
/* ------------------------------------------------------------------ */

export function Card({ className = '', children }: { className?: string; children: ReactNode }) {
  return <div className={`card-bg border border-border rounded-xl ${className}`}>{children}</div>;
}

export function CardHeader({
  title,
  subtitle,
  actions,
}: {
  title: ReactNode;
  subtitle?: ReactNode;
  actions?: ReactNode;
}) {
  return (
    <div className="flex flex-wrap items-start justify-between gap-3 border-b border-border px-5 py-4">
      <div>
        <h2 className="font-display font-semibold text-off-white">{title}</h2>
        {subtitle && <p className="mt-0.5 text-sm text-muted">{subtitle}</p>}
      </div>
      {actions}
    </div>
  );
}

export function CardBody({ className = '', children }: { className?: string; children: ReactNode }) {
  return <div className={`p-5 ${className}`}>{children}</div>;
}

/* ------------------------------------------------------------------ */
/* Badge                                                               */
/* ------------------------------------------------------------------ */

export type BadgeTone = 'acid' | 'green' | 'amber' | 'red' | 'blue' | 'muted';

const BADGE_TONES: Record<BadgeTone, string> = {
  acid: 'bg-acid/15 text-acid',
  green: 'bg-green-500/15 text-green-300',
  amber: 'bg-amber-500/15 text-amber-300',
  red: 'bg-red-500/15 text-red-300',
  blue: 'bg-blue-500/15 text-blue-300',
  muted: 'bg-muted/15 text-muted',
};

export function Badge({ tone = 'muted', className = '', children }: { tone?: BadgeTone; className?: string; children: ReactNode }) {
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-md px-2 py-0.5 text-xs font-medium ${BADGE_TONES[tone]} ${className}`}
    >
      {children}
    </span>
  );
}

/* ------------------------------------------------------------------ */
/* Form primitives (§17 : aria-invalid + aria-describedby)             */
/* ------------------------------------------------------------------ */

export function Field({
  label,
  htmlFor,
  error,
  hint,
  children,
}: {
  label: ReactNode;
  htmlFor: string;
  error?: string | null;
  hint?: ReactNode;
  children: ReactNode;
}) {
  return (
    <div className="space-y-1.5">
      <label htmlFor={htmlFor} className="block text-sm font-medium text-off-white">
        {label}
      </label>
      {children}
      {hint && !error && <p className="text-xs text-muted">{hint}</p>}
      <FormError id={`${htmlFor}-error`} message={error} />
    </div>
  );
}

export function FormError({ id, message }: { id?: string; message?: string | null }) {
  if (!message) return null;
  return (
    <p id={id} role="alert" className="text-sm text-red-400">
      {message}
    </p>
  );
}

const INPUT_BASE =
  'w-full rounded-lg border bg-off-black px-3 py-2 text-sm text-off-white placeholder:text-muted/70 transition-colors focus:outline-none focus:ring-2 focus:ring-acid/50 disabled:opacity-60';

export function Input({
  invalid,
  className = '',
  ...props
}: InputHTMLAttributes<HTMLInputElement> & { invalid?: boolean }) {
  return (
    <input
      className={`${INPUT_BASE} ${invalid ? 'border-red-500/70' : 'border-border focus:border-acid/60'} ${className}`}
      aria-invalid={invalid || undefined}
      {...props}
    />
  );
}

export function TextArea({
  invalid,
  className = '',
  ...props
}: TextareaHTMLAttributes<HTMLTextAreaElement> & { invalid?: boolean }) {
  return (
    <textarea
      className={`${INPUT_BASE} ${invalid ? 'border-red-500/70' : 'border-border focus:border-acid/60'} ${className}`}
      aria-invalid={invalid || undefined}
      {...props}
    />
  );
}

export function Select({
  invalid,
  className = '',
  children,
  ...props
}: SelectHTMLAttributes<HTMLSelectElement> & { invalid?: boolean; children: ReactNode }) {
  return (
    <select
      className={`${INPUT_BASE} ${invalid ? 'border-red-500/70' : 'border-border focus:border-acid/60'} ${className}`}
      aria-invalid={invalid || undefined}
      {...props}
    >
      {children}
    </select>
  );
}

/* ------------------------------------------------------------------ */
/* Feedback visuel                                                    */
/* ------------------------------------------------------------------ */

export function Spinner({ className = '' }: { className?: string }) {
  return (
    <span
      className={`inline-block h-4 w-4 animate-spin rounded-full border-2 border-muted border-t-acid ${className}`}
      role="status"
      aria-label="Chargement"
    />
  );
}

export function Skeleton({ className = '' }: { className?: string }) {
  return <div className={`animate-pulse rounded-lg bg-off-black ${className}`} />;
}

export function EmptyState({
  title,
  description,
  actions,
}: {
  title: ReactNode;
  description?: ReactNode;
  actions?: ReactNode;
}) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 rounded-xl border border-dashed border-border px-6 py-12 text-center">
      <h3 className="font-display text-lg font-medium text-off-white">{title}</h3>
      {description && <p className="max-w-sm text-sm text-muted">{description}</p>}
      {actions && <div className="mt-3">{actions}</div>}
    </div>
  );
}

export function ProgressBar({ value, className = '' }: { value: number; className?: string }) {
  const pct = Math.min(100, Math.max(0, Math.round(value * 100)));
  return (
    <div
      className={`h-1.5 w-full overflow-hidden rounded-full bg-off-black ${className}`}
      role="progressbar"
      aria-valuenow={pct}
      aria-valuemin={0}
      aria-valuemax={100}
    >
      <div className="h-full rounded-full bg-acid transition-all duration-500" style={{ width: `${pct}%` }} />
    </div>
  );
}

export function Stat({
  label,
  value,
  accent,
}: {
  label: ReactNode;
  value: ReactNode;
  accent?: boolean;
}) {
  return (
    <div className="rounded-lg border border-border bg-off-black/60 px-4 py-3">
      <p className="text-xs text-muted">{label}</p>
      <p className={`mt-1 font-display text-xl ${accent ? 'text-acid' : 'text-off-white'}`}>{value}</p>
    </div>
  );
}
