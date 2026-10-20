"use client";

import Link from "next/link";
import { use, useEffect, useState } from "react";
import { ApprovalCard } from "@/components/approvals";
import { ArtifactBrowser } from "@/components/artifacts";
import { Studio } from "@/components/studio";
import { Button, Card, Empty, ErrorBox, Field, Input, Markdown, PageHeader, Select, Spinner, Status, Tabs, Textarea } from "@/components/ui";
import { ACTIVE, api, Approval, Artifact, fmtDate, KnowledgeItem, Page, Project, Task, usd } from "@/lib/api";
import { useAction, useApi } from "@/lib/hooks";

function Overview({ project, reload }: { project: Project; reload: () => void }) {
  const [form, setForm] = useState({ requirements: project.requirements, description: project.description, budget: project.settings.ai_budget_usd,
    fixes: project.settings.max_fix_iterations, network: project.settings.sandbox_network, language: project.language });
  const approvals = useApi<Page<Approval>>(`/approvals?status_=pending&limit=50`, { poll: 4000 });
  const action = useAction();
  const save = () => action.run(async () => {
    await api(`/projects/${project.id}`, { method: "PATCH", json: { requirements: form.requirements, description: form.description, language: form.language,
      settings: { ai_budget_usd: Number(form.budget), max_fix_iterations: Number(form.fixes), sandbox_network: form.network } } });
    reload();
  });
  const start = (workflow: string) => action.run(async () => {
    const task = await api<Task>(`/projects/${project.id}/workflows`, { method: "POST", json: { workflow } });
    window.location.href = `/tasks/${task.id}`;
  });
  const mine = approvals.data?.items.filter((a) => a.project_id === project.id) ?? [];
  const stats = project.stats;
  return (
    <div className="grid gap-4 lg:grid-cols-[1fr_320px]">
      <div className="space-y-4">
        {mine.map((a) => <ApprovalCard key={a.id} approval={a} onDone={() => { approvals.reload(); reload(); }} />)}
        <Card title="Requisitos">
          <div className="space-y-3">
            <Field label="Descrição"><Input value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} /></Field>
            <Field label="Objetivo e requisitos"><Textarea rows={7} value={form.requirements} onChange={(e) => setForm({ ...form, requirements: e.target.value })} /></Field>
            <div className="grid gap-3 sm:grid-cols-4">
              <Field label="Linguagem">
                <Select className="w-full" value={form.language} onChange={(e) => setForm({ ...form, language: e.target.value })}>
                  <option value="python">Python</option><option value="javascript">JavaScript</option>
                </Select>
              </Field>
              <Field label="Orçamento de IA (US$)"><Input type="number" min={0} step="0.5" value={form.budget} onChange={(e) => setForm({ ...form, budget: Number(e.target.value) })} /></Field>
              <Field label="Correções automáticas"><Input type="number" min={0} max={5} value={form.fixes} onChange={(e) => setForm({ ...form, fixes: Number(e.target.value) })} /></Field>
              <Field label="Rede no sandbox" hint="Exige aprovação a cada execução">
                <Select className="w-full" value={form.network ? "1" : "0"} onChange={(e) => setForm({ ...form, network: e.target.value === "1" })}>
                  <option value="0">Desabilitada</option><option value="1">Solicitar</option>
                </Select>
              </Field>
            </div>
            <ErrorBox error={action.error} />
            <Button onClick={save} disabled={action.busy}>Salvar requisitos</Button>
          </div>
        </Card>
      </div>
      <div className="space-y-4">
        <Card title="Iniciar">
          <div className="space-y-2">
            <Button className="w-full" onClick={() => start("mission")} disabled={action.busy}>Missão completa</Button>
            <p className="text-xs text-muted">Pesquisa → plano (IA) → sua aprovação → código (IA) → testes isolados → segurança → entrega.</p>
            <Button className="w-full" variant="secondary" onClick={() => start("plan")} disabled={action.busy}>Somente plano</Button>
            <Button className="w-full" variant="secondary" onClick={() => start("develop")} disabled={action.busy || !project.approved_plan_artifact_id}>Nova iteração de código</Button>
          </div>
        </Card>
        <Card title="Indicadores">
          {stats && (
            <dl className="space-y-1 text-sm">
              <div className="flex justify-between"><dt className="text-muted">Status</dt><dd><Status value={project.status} /></dd></div>
              <div className="flex justify-between"><dt className="text-muted">Custo de IA</dt><dd>{usd(stats.ai_cost_usd)} / US$ {stats.budget_usd}</dd></div>
              <div className="flex justify-between"><dt className="text-muted">Tokens</dt><dd>{(stats.input_tokens + stats.output_tokens).toLocaleString("pt-BR")}</dd></div>
              <div className="flex justify-between"><dt className="text-muted">Aprovações pendentes</dt><dd>{stats.pending_approvals}</dd></div>
              {Object.entries(stats.workflows_by_status).map(([k, v]) => (
                <div key={k} className="flex justify-between"><dt className="text-muted">Fluxos: <Status value={k} /></dt><dd>{v}</dd></div>
              ))}
              <div className="flex justify-between"><dt className="text-muted">Plano aprovado</dt><dd>{project.approved_plan_artifact_id ? "sim" : "não"}</dd></div>
            </dl>
          )}
        </Card>
      </div>
    </div>
  );
}

function Workflows({ projectId }: { projectId: string }) {
  const { data } = useApi<Page<Task>>(`/projects/${projectId}/tasks?limit=50`, { poll: 4000 });
  if (!data) return <Spinner />;
  if (!data.items.length) return <Empty>Nenhum fluxo executado.</Empty>;
  return (
    <div className="overflow-x-auto rounded-lg border border-line bg-panel">
      <table className="w-full text-sm">
        <thead className="bg-subtle text-left text-xs text-muted"><tr><th className="p-2">Fluxo</th><th className="p-2">Status</th><th className="p-2">Criado</th><th className="p-2">Erro</th></tr></thead>
        <tbody>
          {data.items.map((t) => (
            <tr key={t.id} className="border-t border-line">
              <td className="p-2"><Link className="hover:underline" href={`/tasks/${t.id}`}>{t.title}</Link></td>
              <td className="p-2"><Status value={t.status} /></td>
              <td className="p-2 text-xs text-muted">{fmtDate(t.created_at)}</td>
              <td className="max-w-md truncate p-2 text-xs text-danger" title={t.error ?? ""}>{t.error}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function Memory({ projectId }: { projectId: string }) {
  const memory = useApi<Page<KnowledgeItem>>(`/knowledge/projects/${projectId}/memory?limit=100`);
  const recs = useApi<{ keywords: string[]; groups: Record<string, { total_matches: number; items: KnowledgeItem[] }> }>(`/knowledge/recommendations?project_id=${projectId}`);
  const [form, setForm] = useState({ title: "", content: "" });
  const action = useAction();
  const add = () => action.run(async () => {
    await api(`/knowledge/projects/${projectId}/memory`, { method: "POST", json: { ...form, item_type: "decision" } });
    setForm({ title: "", content: "" });
    memory.reload();
  });
  const remove = (id: string) => action.run(async () => { await api(`/knowledge/projects/${projectId}/memory/${id}`, { method: "DELETE" }); memory.reload(); });
  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <Card title="Memória e decisões do projeto" actions={<a className="text-xs text-accent underline" href="#" onClick={async (e) => {
        e.preventDefault();
        const text = await api<unknown>(`/knowledge/projects/${projectId}/memory/export`);
        const blob = new Blob([JSON.stringify(text, null, 2)], { type: "application/json" });
        const url = URL.createObjectURL(blob);
        const link = document.createElement("a");
        link.href = url; link.download = `memoria-${projectId}.json`; link.click(); URL.revokeObjectURL(url);
      }}>Exportar JSON</a>}>
        <div className="mb-4 space-y-2">
          <Input placeholder="Título da decisão" value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} />
          <Textarea rows={2} placeholder="Contexto e justificativa" value={form.content} onChange={(e) => setForm({ ...form, content: e.target.value })} />
          <ErrorBox error={action.error} />
          <Button onClick={add} disabled={action.busy || !form.title || !form.content}>Registrar decisão</Button>
        </div>
        {!memory.data?.items.length ? <Empty>Sem registros.</Empty> : (
          <ul className="divide-y divide-line text-sm">
            {memory.data.items.map((m) => (
              <li key={m.id} className="py-2">
                <div className="flex justify-between gap-2"><span className="font-medium">{m.title}</span>
                  <button className="text-xs text-danger hover:underline" onClick={() => remove(m.id)}>excluir</button></div>
                <p className="whitespace-pre-wrap text-xs text-muted">{m.description}</p>
                <p className="text-xs text-muted">{m.item_type} · origem {m.origin_path ?? "—"} · {fmtDate(m.created_at)}</p>
              </li>
            ))}
          </ul>
        )}
      </Card>
      <Card title="Recomendações da base de conhecimento">
        {!recs.data ? <Spinner /> : !Object.keys(recs.data.groups).length ? (
          <Empty>Nenhuma correspondência. Indexe catálogos em <Link className="text-accent underline" href="/repositories">Engenharia reversa</Link>.</Empty>
        ) : (
          <div className="space-y-3 text-sm">
            <p className="text-xs text-muted">Palavras-chave: {recs.data.keywords.join(", ")}</p>
            {Object.entries(recs.data.groups).map(([kind, g]) => (
              <div key={kind}>
                <h4 className="text-xs font-semibold uppercase text-muted">{kind} ({g.total_matches})</h4>
                <ul className="mt-1 space-y-1">
                  {g.items.map((i) => (
                    <li key={i.id}><a className="text-accent underline" href={i.url ?? "#"} target="_blank" rel="noreferrer">{i.title}</a>
                      <span className="text-xs text-muted"> — {i.description.slice(0, 100)} · fonte: {i.source_name}</span></li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        )}
      </Card>
    </div>
  );
}

function Activity({ projectId }: { projectId: string }) {
  const { data } = useApi<Page<{ id: string; action: string; actor: string; details: Record<string, unknown>; created_at: string }>>(`/projects/${projectId}/activity?limit=100`, { poll: 8000 });
  if (!data) return <Spinner />;
  return (
    <ul className="divide-y divide-line rounded-lg border border-line bg-panel text-sm">
      {data.items.map((e) => (
        <li key={e.id} className="flex flex-wrap justify-between gap-2 px-3 py-2">
          <span><code className="text-xs">{e.action}</code> <span className="text-muted">por {e.actor}</span>
            {Object.keys(e.details).length > 0 && <span className="ml-2 text-xs text-muted">{JSON.stringify(e.details).slice(0, 140)}</span>}</span>
          <span className="text-xs text-muted">{fmtDate(e.created_at)}</span>
        </li>
      ))}
    </ul>
  );
}

export default function ProjectPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const project = useApi<Project>(`/projects/${id}`, { poll: 6000 });
  const action = useAction();
  const [tab, setTab] = useState<string | undefined>(undefined);
  useEffect(() => setTab(new URLSearchParams(window.location.search).get("tab") ?? "overview"), []);
  if (project.loading && !project.data) return <Spinner />;
  if (!project.data) return <ErrorBox error={project.error} />;
  const p = project.data;
  const requestDelete = () => action.run(async () => {
    if (!confirm("Solicitar exclusão definitiva? Uma aprovação será criada.")) return;
    await api(`/projects/${p.id}`, { method: "DELETE" });
    window.location.href = "/approvals";
  });
  if (!tab) return <Spinner />;
  return (
    <>
      <PageHeader title={p.name} subtitle={<>Criado {fmtDate(p.created_at)} · <Status value={p.status} /> {p.stats && Object.keys(p.stats.workflows_by_status).some((s) => ACTIVE.includes(s)) && "· fluxo em andamento"}</>}
        actions={<Button variant="ghost" className="text-danger" onClick={requestDelete}>Excluir projeto</Button>} />
      <ErrorBox error={action.error} />
      <Tabs initial={tab} tabs={[
        { key: "overview", label: "Visão geral", content: <Overview project={p} reload={project.reload} /> },
        { key: "studio", label: "Studio", content: <Studio project={p} onWorkflow={project.reload} /> },
        { key: "workflows", label: "Fluxos", content: <Workflows projectId={p.id} /> },
        { key: "artifacts", label: "Planos e relatórios", content: <ArtifactBrowser path={`/projects/${p.id}/artifacts?limit=100`} /> },
        { key: "memory", label: "Memória e recomendações", content: <Memory projectId={p.id} /> },
        { key: "activity", label: "Histórico", content: <Activity projectId={p.id} /> },
      ]} />
    </>
  );
}
