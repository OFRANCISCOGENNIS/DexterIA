"use client";

import { FormEvent, useState } from "react";
import { api, Page, Project } from "@/lib/api";
import { useAction, useApi } from "@/lib/hooks";
import { Button, Card, cx, Empty, ErrorBox, Field, Input, Select } from "./ui";

type PathItem = { id: string; position: number; stage: string; item_type: string; title: string; url: string | null;
  source_name: string | null; reason: string; status: "todo" | "doing" | "done" };
type LearningPath = { id: string; title: string; goal: string; keywords: string[]; project_id: string | null; total: number;
  done: number; progress: number; items: PathItem[]; created_at: string };

const STATUS_LABEL = { todo: "a fazer", doing: "estudando", done: "concluído" } as const;
const NEXT: Record<PathItem["status"], PathItem["status"]> = { todo: "doing", doing: "done", done: "todo" };

function PathCard({ path, onChange }: { path: LearningPath; onChange: () => void }) {
  const action = useAction();
  const setStatus = (item: PathItem) => action.run(async () => {
    await api(`/learning/paths/${path.id}/items/${item.id}`, { method: "PATCH", json: { status: NEXT[item.status] } });
    onChange();
  });
  const remove = () => action.run(async () => {
    if (!confirm(`Excluir a trilha "${path.title}"?`)) return;
    await api(`/learning/paths/${path.id}`, { method: "DELETE" });
    onChange();
  });
  const stages = [...new Set(path.items.map((i) => i.stage))];
  const pct = Math.round(path.progress * 100);
  return (
    <Card title={path.title} actions={<Button variant="ghost" className="text-xs text-danger" onClick={remove}>Excluir</Button>}>
      <div className="mb-3">
        <div className="mb-1 flex justify-between text-xs text-muted"><span>Palavras-chave: {path.keywords.join(", ")}</span><span>{path.done}/{path.total} · {pct}%</span></div>
        <div className="h-2 overflow-hidden rounded-full bg-subtle" role="progressbar" aria-valuenow={pct} aria-valuemin={0} aria-valuemax={100}>
          <div className="h-full bg-ok transition-all" style={{ width: `${pct}%` }} />
        </div>
      </div>
      <ErrorBox error={action.error} />
      {stages.map((stage) => (
        <div key={stage} className="mb-3">
          <h4 className="mb-1 text-xs font-semibold uppercase text-muted">{stage}</h4>
          <ul className="space-y-1">
            {path.items.filter((i) => i.stage === stage).map((i) => (
              <li key={i.id} className="flex items-start gap-2 text-sm">
                <button onClick={() => setStatus(i)} disabled={action.busy} title="Alterar status"
                  className={cx("mt-0.5 shrink-0 rounded-full border px-2 text-xs", i.status === "done" ? "border-ok bg-ok/15 text-ok" : i.status === "doing" ? "border-accent text-accent" : "border-line text-muted")}>
                  {STATUS_LABEL[i.status]}
                </button>
                <span className={i.status === "done" ? "text-muted line-through" : ""}>
                  <a className="text-accent underline" href={i.url ?? "#"} target="_blank" rel="noreferrer noopener">{i.title}</a>
                  <span className="text-xs text-muted"> — {i.reason} · fonte: {i.source_name}</span>
                </span>
              </li>
            ))}
          </ul>
        </div>
      ))}
    </Card>
  );
}

export function LearningPaths() {
  const paths = useApi<LearningPath[]>("/learning/paths");
  const projects = useApi<Page<Project>>("/projects?limit=200");
  const [form, setForm] = useState({ project_id: "", goal: "" });
  const action = useAction();
  const create = (e: FormEvent) => {
    e.preventDefault();
    action.run(async () => {
      await api("/learning/paths", { method: "POST", json: { project_id: form.project_id || null, goal: form.goal } });
      setForm({ project_id: "", goal: "" });
      paths.reload();
    });
  };
  return (
    <div className="space-y-4">
      <Card title="Nova trilha de estudo">
        <form onSubmit={create} className="grid gap-3 md:grid-cols-[240px_1fr_auto]">
          <Field label="A partir de um projeto">
            <Select className="w-full" value={form.project_id} onChange={(e) => setForm({ ...form, project_id: e.target.value })}>
              <option value="">(nenhum)</option>
              {projects.data?.items.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
            </Select>
          </Field>
          <Field label="ou um objetivo" hint="Os materiais são escolhidos na base de conhecimento por correspondência com estes termos.">
            <Input value={form.goal} onChange={(e) => setForm({ ...form, goal: e.target.value })} placeholder="Ex.: aprender python, sql e algoritmos" />
          </Field>
          <div className="flex items-end pb-5"><Button type="submit" disabled={action.busy || (!form.project_id && !form.goal.trim())}>{action.busy ? "Montando…" : "Montar trilha"}</Button></div>
        </form>
        <ErrorBox error={action.error} />
      </Card>
      {!paths.data?.length ? <Empty>Nenhuma trilha criada.</Empty> : paths.data.map((p) => <PathCard key={p.id} path={p} onChange={paths.reload} />)}
    </div>
  );
}
