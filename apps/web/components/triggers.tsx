"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import { api, fmtDate, Page, Project, Repository } from "@/lib/api";
import { useAction, useApi } from "@/lib/hooks";
import { Button, Card, Empty, ErrorBox, Field, Input, Select } from "./ui";

type Trigger = {
  id: string; name: string; workflow: string; interval_minutes: number; enabled: boolean; project_id: string | null;
  repository_id: string | null; next_run_at: string; last_run_at: string | null; last_task_id: string | null;
  last_error: string | null; run_count: number;
};

const WORKFLOWS: Record<string, { label: string; target: "project" | "repository" }> = {
  test: { label: "Executar testes do projeto", target: "project" },
  analyze_repository: { label: "Reanalisar repositório", target: "repository" },
  ingest_knowledge: { label: "Reindexar catálogo", target: "repository" },
};

const INTERVALS = [
  { value: 60, label: "a cada hora" }, { value: 360, label: "a cada 6 horas" },
  { value: 1440, label: "diariamente" }, { value: 10080, label: "semanalmente" },
];

function every(minutes: number) {
  return INTERVALS.find((i) => i.value === minutes)?.label ?? `a cada ${minutes} min`;
}

export function Triggers() {
  const triggers = useApi<Trigger[]>("/triggers", { poll: 15000 });
  const projects = useApi<Page<Project>>("/projects?limit=200");
  const repos = useApi<Page<Repository>>("/repositories?limit=200");
  const [form, setForm] = useState({ name: "", workflow: "test", target: "", interval: 1440 });
  const action = useAction();
  const target = WORKFLOWS[form.workflow].target;
  const options = target === "project"
    ? (projects.data?.items ?? []).map((p) => ({ id: p.id, label: p.name }))
    : (repos.data?.items ?? []).filter((r) => r.source_type !== "upload").map((r) => ({ id: r.id, label: r.name }));
  const names: Record<string, string> = Object.fromEntries([
    ...(projects.data?.items ?? []).map((p) => [p.id, p.name]),
    ...(repos.data?.items ?? []).map((r) => [r.id, r.name]),
  ]);

  const create = (e: FormEvent) => {
    e.preventDefault();
    action.run(async () => {
      await api("/triggers", { method: "POST", json: {
        name: form.name, workflow: form.workflow, interval_minutes: form.interval,
        [target === "project" ? "project_id" : "repository_id"]: form.target,
      } });
      setForm({ ...form, name: "", target: "" });
      triggers.reload();
    });
  };
  const toggle = (t: Trigger) => action.run(async () => { await api(`/triggers/${t.id}`, { method: "PATCH", json: { enabled: !t.enabled } }); triggers.reload(); });
  const remove = (t: Trigger) => action.run(async () => {
    if (!confirm(`Remover o gatilho "${t.name}"?`)) return;
    await api(`/triggers/${t.id}`, { method: "DELETE" });
    triggers.reload();
  });

  return (
    <Card title="Gatilhos agendados" className="mb-6">
      <p className="mb-3 text-xs text-muted">
        Só fluxos sem geração de código por IA podem ser agendados (testes, análise e indexação), então nada é executado sem
        aprovação e o orçamento de IA não é consumido. Se a execução anterior ainda estiver em andamento, a próxima é pulada.
      </p>
      <form onSubmit={create} className="mb-4 grid gap-3 md:grid-cols-5">
        <Field label="Nome"><Input required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="Testes noturnos" /></Field>
        <Field label="Fluxo">
          <Select className="w-full" value={form.workflow} onChange={(e) => setForm({ ...form, workflow: e.target.value, target: "" })}>
            {Object.entries(WORKFLOWS).map(([k, w]) => <option key={k} value={k}>{w.label}</option>)}
          </Select>
        </Field>
        <Field label={target === "project" ? "Projeto" : "Repositório"}>
          <Select className="w-full" required value={form.target} onChange={(e) => setForm({ ...form, target: e.target.value })}>
            <option value="">Selecione…</option>
            {options.map((o) => <option key={o.id} value={o.id}>{o.label}</option>)}
          </Select>
        </Field>
        <Field label="Frequência">
          <Select className="w-full" value={form.interval} onChange={(e) => setForm({ ...form, interval: Number(e.target.value) })}>
            {INTERVALS.map((i) => <option key={i.value} value={i.value}>{i.label}</option>)}
          </Select>
        </Field>
        <div className="flex items-end"><Button type="submit" disabled={action.busy || !form.target}>Agendar</Button></div>
      </form>
      <ErrorBox error={action.error} />
      {!triggers.data?.length ? <Empty>Nenhum gatilho agendado.</Empty> : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="text-left text-xs text-muted">
              <tr><th className="p-2">Gatilho</th><th className="p-2">Alvo</th><th className="p-2">Frequência</th><th className="p-2">Próxima</th><th className="p-2">Última</th><th className="p-2"></th></tr>
            </thead>
            <tbody>
              {triggers.data.map((t) => (
                <tr key={t.id} className="border-t border-line align-top">
                  <td className="p-2"><div className="font-medium">{t.name}</div><div className="text-xs text-muted">{WORKFLOWS[t.workflow]?.label}</div></td>
                  <td className="p-2 text-xs">{names[t.project_id && t.workflow === "test" ? t.project_id : t.repository_id ?? ""] ?? "—"}</td>
                  <td className="p-2 text-xs">{every(t.interval_minutes)}</td>
                  <td className="p-2 text-xs">{t.enabled ? fmtDate(t.next_run_at) : "pausado"}</td>
                  <td className="p-2 text-xs">
                    {t.last_task_id ? <Link className="text-accent underline" href={`/tasks/${t.last_task_id}`}>{fmtDate(t.last_run_at)}</Link> : "—"}
                    <span className="text-muted"> · {t.run_count} execução(ões)</span>
                    {t.last_error && <div className="text-warn">{t.last_error}</div>}
                  </td>
                  <td className="whitespace-nowrap p-2">
                    <Button variant="ghost" className="text-xs" onClick={() => toggle(t)}>{t.enabled ? "Pausar" : "Retomar"}</Button>
                    <Button variant="ghost" className="text-xs text-danger" onClick={() => remove(t)}>Remover</Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Card>
  );
}
