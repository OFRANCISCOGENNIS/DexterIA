"use client";

import Link from "next/link";
import { useState } from "react";
import { Triggers } from "@/components/triggers";
import { Button, Card, Empty, PageHeader, Select, Spinner, Status } from "@/components/ui";
import { ACTIVE, api, fmtDate, Page, Task } from "@/lib/api";
import { useApi } from "@/lib/hooks";

type Workflow = { name: string; title: string; description: string; requires: string; steps: { key: string; agent: string; title: string; depends_on: string[]; optional: boolean }[] };

export default function AutomationsPage() {
  const workflows = useApi<Workflow[]>("/workflows");
  const [status, setStatus] = useState("");
  const tasks = useApi<Page<Task>>(`/tasks?limit=100${status ? `&status=${status}` : ""}`, { poll: 4000 });
  const cancel = async (id: string) => { await api(`/tasks/${id}/cancel`, { method: "POST" }); tasks.reload(); };
  return (
    <>
      <PageHeader title="Automações" subtitle="Fluxos multiagente encadeados, com dependências, tentativas limitadas, cancelamento e aprovação humana." />
      <Triggers />
      <div className="mb-6 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
        {workflows.data?.map((w) => (
          <div key={w.name} className="rounded-lg border border-line bg-panel p-4">
            <h3 className="font-medium">{w.title}</h3>
            <p className="mt-1 text-xs text-muted">{w.description}</p>
            <ol className="mt-2 space-y-0.5 text-xs">
              {w.steps.map((s) => <li key={s.key}><code>{s.agent}</code> — {s.title}{s.optional && " (opcional)"}{s.depends_on.length > 0 && <span className="text-muted"> ← {s.depends_on.join(", ")}</span>}</li>)}
            </ol>
            <p className="mt-2 text-xs text-muted">Inicia a partir de: {w.requires === "project" ? "um projeto" : "um repositório"}</p>
          </div>
        ))}
      </div>
      <Card title="Histórico de execuções" actions={
        <Select value={status} onChange={(e) => setStatus(e.target.value)} aria-label="Filtrar por status">
          <option value="">Todos</option>
          {["queued", "running", "awaiting_approval", "succeeded", "failed", "cancelled"].map((s) => <option key={s} value={s}>{s}</option>)}
        </Select>}>
        {!tasks.data ? <Spinner /> : !tasks.data.items.length ? <Empty>Nenhuma execução.</Empty> : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="text-left text-xs text-muted"><tr><th className="p-2">Fluxo</th><th className="p-2">Objetivo</th><th className="p-2">Status</th><th className="p-2">Criado</th><th className="p-2"></th></tr></thead>
              <tbody>
                {tasks.data.items.map((t) => (
                  <tr key={t.id} className="border-t border-line">
                    <td className="p-2"><Link className="hover:underline" href={`/tasks/${t.id}`}>{t.title}</Link></td>
                    <td className="max-w-sm truncate p-2 text-xs text-muted">{t.objective}</td>
                    <td className="p-2"><Status value={t.status} /></td>
                    <td className="p-2 text-xs text-muted">{fmtDate(t.created_at)}</td>
                    <td className="p-2">{ACTIVE.includes(t.status) && <Button variant="ghost" className="text-xs text-danger" onClick={() => cancel(t.id)}>Cancelar</Button>}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </>
  );
}
