"use client";

import Link from "next/link";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { ButtonHTMLAttributes, InputHTMLAttributes, ReactNode, SelectHTMLAttributes, TextareaHTMLAttributes, useState } from "react";

export function cx(...classes: (string | false | null | undefined)[]) {
  return classes.filter(Boolean).join(" ");
}

export function Button({ variant = "primary", className, ...props }: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: "primary" | "secondary" | "danger" | "ghost" }) {
  const styles = {
    primary: "bg-accent text-white hover:opacity-90",
    secondary: "border border-line bg-panel hover:bg-subtle",
    danger: "bg-danger text-white hover:opacity-90",
    ghost: "hover:bg-subtle",
  }[variant];
  return (
    <button
      {...props}
      className={cx("inline-flex items-center justify-center gap-2 rounded-md px-3 py-1.5 text-sm font-medium transition disabled:cursor-not-allowed disabled:opacity-50 focus-visible:outline-2 focus-visible:outline-accent", styles, className)}
    />
  );
}

export function Input(props: InputHTMLAttributes<HTMLInputElement>) {
  return <input {...props} className={cx("w-full rounded-md border border-line bg-panel px-3 py-2 text-sm outline-none focus:border-accent", props.className)} />;
}

export function Textarea(props: TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return <textarea {...props} className={cx("w-full rounded-md border border-line bg-panel px-3 py-2 text-sm outline-none focus:border-accent", props.className)} />;
}

export function Select(props: SelectHTMLAttributes<HTMLSelectElement>) {
  return <select {...props} className={cx("rounded-md border border-line bg-panel px-3 py-2 text-sm outline-none focus:border-accent", props.className)} />;
}

export function Field({ label, hint, children }: { label: string; hint?: string; children: ReactNode }) {
  return (
    <label className="block space-y-1">
      <span className="text-sm font-medium">{label}</span>
      {children}
      {hint && <span className="block text-xs text-muted">{hint}</span>}
    </label>
  );
}

export function Card({ title, actions, children, className }: { title?: ReactNode; actions?: ReactNode; children: ReactNode; className?: string }) {
  return (
    <section className={cx("rounded-lg border border-line bg-panel", className)}>
      {(title || actions) && (
        <header className="flex flex-wrap items-center justify-between gap-2 border-b border-line px-4 py-3">
          <h2 className="text-sm font-semibold">{title}</h2>
          <div className="flex flex-wrap gap-2">{actions}</div>
        </header>
      )}
      <div className="p-4">{children}</div>
    </section>
  );
}

const STATUS: Record<string, [string, string]> = {
  succeeded: ["concluída", "bg-ok/15 text-ok"],
  failed: ["falhou", "bg-danger/15 text-danger"],
  running: ["executando", "bg-accent/15 text-accent"],
  queued: ["na fila", "bg-subtle text-muted"],
  pending: ["pendente", "bg-warn/15 text-warn"],
  awaiting_approval: ["aguarda aprovação", "bg-warn/15 text-warn"],
  cancelled: ["cancelada", "bg-subtle text-muted"],
  skipped: ["pulada", "bg-subtle text-muted"],
  approved: ["aprovada", "bg-ok/15 text-ok"],
  rejected: ["rejeitada", "bg-danger/15 text-danger"],
  interrupted: ["interrompida", "bg-warn/15 text-warn"],
  analyzed: ["analisado", "bg-ok/15 text-ok"],
  imported: ["importado", "bg-accent/15 text-accent"],
  importing: ["importando", "bg-accent/15 text-accent"],
  registered: ["registrado", "bg-subtle text-muted"],
  error: ["erro", "bg-danger/15 text-danger"],
  delivered: ["entregue", "bg-ok/15 text-ok"],
  needs_attention: ["requer atenção", "bg-warn/15 text-warn"],
  planned: ["plano gerado", "bg-accent/15 text-accent"],
  approved_plan: ["plano aprovado", "bg-ok/15 text-ok"],
  draft: ["rascunho", "bg-subtle text-muted"],
  requirements: ["requisitos", "bg-subtle text-muted"],
};

export function Status({ value }: { value: string }) {
  const [label, style] = STATUS[value] ?? [value, "bg-subtle text-muted"];
  return <span className={cx("inline-flex items-center whitespace-nowrap rounded-full px-2 py-0.5 text-xs font-medium", style)}>{label}</span>;
}

export function Empty({ children }: { children: ReactNode }) {
  return <p className="rounded-md border border-dashed border-line p-6 text-center text-sm text-muted">{children}</p>;
}

export function ErrorBox({ error }: { error: string | null }) {
  if (!error) return null;
  return <p role="alert" className="rounded-md border border-danger/40 bg-danger/10 px-3 py-2 text-sm text-danger">{error}</p>;
}

export function Spinner({ label = "Carregando…" }: { label?: string }) {
  return (
    <p className="flex items-center gap-2 text-sm text-muted" aria-live="polite">
      <span className="h-3 w-3 animate-spin rounded-full border-2 border-accent border-t-transparent" />
      {label}
    </p>
  );
}

export function Markdown({ children }: { children: string }) {
  return (
    <div className="prose-genisia">
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={{ a: ({ href, children }) => <a href={href} target="_blank" rel="noreferrer noopener">{children}</a> }}>
        {children}
      </ReactMarkdown>
    </div>
  );
}

export function Tabs({ tabs, initial }: { tabs: { key: string; label: string; content: ReactNode }[]; initial?: string }) {
  const [active, setActive] = useState(initial ?? tabs[0]?.key);
  return (
    <div>
      <div role="tablist" className="mb-4 flex gap-1 overflow-x-auto border-b border-line">
        {tabs.map((t) => (
          <button
            key={t.key}
            role="tab"
            aria-selected={active === t.key}
            onClick={() => setActive(t.key)}
            className={cx("whitespace-nowrap border-b-2 px-3 py-2 text-sm", active === t.key ? "border-accent font-medium text-fg" : "border-transparent text-muted hover:text-fg")}
          >
            {t.label}
          </button>
        ))}
      </div>
      {tabs.find((t) => t.key === active)?.content}
    </div>
  );
}

export function PageHeader({ title, subtitle, actions }: { title: string; subtitle?: ReactNode; actions?: ReactNode }) {
  return (
    <div className="mb-6 flex flex-wrap items-end justify-between gap-3">
      <div>
        <h1 className="text-xl font-semibold">{title}</h1>
        {subtitle && <p className="mt-1 text-sm text-muted">{subtitle}</p>}
      </div>
      <div className="flex flex-wrap gap-2">{actions}</div>
    </div>
  );
}

export function Stat({ label, value, href }: { label: string; value: ReactNode; href?: string }) {
  const inner = (
    <div className="rounded-lg border border-line bg-panel p-4">
      <div className="text-xs uppercase tracking-wide text-muted">{label}</div>
      <div className="mt-1 text-2xl font-semibold tabular-nums">{value}</div>
    </div>
  );
  return href ? <Link href={href} className="block hover:opacity-90">{inner}</Link> : inner;
}
