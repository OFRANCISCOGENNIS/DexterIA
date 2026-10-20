"use client";

import { useEffect, useState } from "react";
import { api, Artifact, fmtDate, Page } from "@/lib/api";
import { useApi } from "@/lib/hooks";
import { Card, Empty, Markdown, Spinner } from "./ui";

export function ArtifactBrowser({ path }: { path: string }) {
  const { data } = useApi<Page<Artifact> | Artifact[]>(path, { poll: 6000 });
  const [open, setOpen] = useState<Artifact | null>(null);
  const items = Array.isArray(data) ? data : data?.items ?? [];
  useEffect(() => {
    if (!open && items.length) api<Artifact>(`/artifacts/${items[0].id}`).then(setOpen).catch(() => {});
  }, [items.length]); // eslint-disable-line react-hooks/exhaustive-deps
  if (!data) return <Spinner />;
  if (!items.length) return <Empty>Nenhum artefato gerado.</Empty>;
  return (
    <div className="grid gap-4 lg:grid-cols-[260px_1fr]">
      <ul className="space-y-1">
        {items.map((a) => (
          <li key={a.id}>
            <button onClick={() => api<Artifact>(`/artifacts/${a.id}`).then(setOpen)} className={`w-full rounded-md border px-3 py-2 text-left text-sm ${open?.id === a.id ? "border-accent bg-subtle" : "border-line bg-panel hover:bg-subtle"}`}>
              <div className="font-medium">{a.title}</div>
              <div className="text-xs text-muted">{a.kind} · {fmtDate(a.created_at)}</div>
            </button>
          </li>
        ))}
      </ul>
      <Card title={open?.title ?? "Artefato"}>{open ? <Markdown>{open.content ?? ""}</Markdown> : <Spinner />}</Card>
    </div>
  );
}

