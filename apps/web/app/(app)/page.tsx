"use client";

import Link from "next/link";
import { Card, Empty, ErrorBox, PageHeader, Spinner, Stat, Status } from "@/components/ui";
import { fmtDate, usd } from "@/lib/api";
import { useApi } from "@/lib/hooks";

type TaskRow = { id: string; title: string; status: string; project_id: string | null; error: string | null; created_at: string };
type Dashboard = {
  counts: { projects: number; repositories: number; knowledge_items: number; pending_approvals: number; workflows_by_status: Record<string, number> };
  ai_usage: { cost_usd: number; input_tokens: number; output_tokens: number; note: string };
  recent_projects: { id: string; name: string; status: string; updated_at: string }[];
  active_tasks: TaskRow[];
  failed_tasks: TaskRow[];
  activity: { action: string; actor: string; created_at: string; details: Record<string, unknown> }[];
};

export default function DashboardPage() {
  const { data, error, loading } = useApi<Dashboard>("/dashboard", { poll: 5000 });
  if (loading && !data) return <Spinner />;
  if (!data) return <ErrorBox error={error} />;
  const wf = data.counts.workflows_by_status;
  const running = (wf.running ?? 0) + (wf.queued ?? 0) + (wf.awaiting_approval ?? 0);
  return (
    <>
      <PageHeader title="Dashboard" subtitle="Dados reais do sistema. Métricas vazias indicam que ainda não há execuções."
        actions={<Link href="/projects?new=1" className="rounded-md bg-accent px-3 py-1.5 text-sm font-medium text-white">Nova missão</Link>} />
      <ErrorBox error={error} />
      <div className="mb-6 grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-6">
        <Stat label="Projetos" value={data.counts.projects} href="/projects" />
        <Stat label="Fluxos ativos" value={running} href="/automations" />
        <Stat label="Concluídos" value={wf.succeeded ?? 0} href="/automations" />
        <Stat label="Com falha" value={wf.failed ?? 0} href="/automations" />
        <Stat label="Aprovações pendentes" value={data.counts.pending_approvals} href="/approvals" />
        <Stat label="Custo estimado de IA" value={usd(data.ai_usage.cost_usd)} href="/agents" />
      </div>
      <div className="grid gap-4 lg:grid-cols-2">
        <Card title="Tarefas em execução">
          {data.active_tasks.length === 0 ? <Empty>Nenhum fluxo em execução.</Empty> : (
            <ul className="divide-y divide-line">
              {data.active_tasks.map((t) => (
                <li key={t.id} className="flex items-center justify-between gap-2 py-2 text-sm">
                  <Link href={`/tasks/${t.id}`} className="truncate hover:underline">{t.title}</Link>
                  <Status value={t.status} />
                </li>
              ))}
            </ul>
          )}
        </Card>
        <Card title="Erros que exigem atenção">
          {data.failed_tasks.length === 0 ? <Empty>Nenhuma falha registrada.</Empty> : (
            <ul className="divide-y divide-line">
              {data.failed_tasks.map((t) => (
                <li key={t.id} className="py-2 text-sm">
                  <Link href={`/tasks/${t.id}`} className="font-medium hover:underline">{t.title}</Link>
                  <p className="line-clamp-2 text-xs text-danger">{t.error ?? "Falha"}</p>
                </li>
              ))}
            </ul>
          )}
        </Card>
        <Card title="Projetos recentes">
          {data.recent_projects.length === 0 ? <Empty>Nenhum projeto ainda. <Link className="text-accent underline" href="/projects?new=1">Criar o primeiro</Link></Empty> : (
            <ul className="divide-y divide-line">
              {data.recent_projects.map((p) => (
                <li key={p.id} className="flex items-center justify-between gap-2 py-2 text-sm">
                  <Link href={`/projects/${p.id}`} className="truncate hover:underline">{p.name}</Link>
                  <span className="flex items-center gap-2"><Status value={p.status} /><span className="text-xs text-muted">{fmtDate(p.updated_at)}</span></span>
                </li>
              ))}
            </ul>
          )}
        </Card>
        <Card title="Atividade recente">
          {data.activity.length === 0 ? <Empty>Sem atividade.</Empty> : (
            <ul className="space-y-1.5 text-sm">
              {data.activity.map((e, i) => (
                <li key={i} className="flex justify-between gap-3">
                  <span className="truncate"><code className="text-xs">{e.action}</code> <span className="text-muted">por {e.actor}</span></span>
                  <span className="shrink-0 text-xs text-muted">{fmtDate(e.created_at)}</span>
                </li>
              ))}
            </ul>
          )}
        </Card>
      </div>
      <p className="mt-4 text-xs text-muted">
        Uso de IA: {data.ai_usage.input_tokens.toLocaleString("pt-BR")} tokens de entrada · {data.ai_usage.output_tokens.toLocaleString("pt-BR")} de saída. {data.ai_usage.note}
        {" "}Base de conhecimento: {data.counts.knowledge_items.toLocaleString("pt-BR")} itens · {data.counts.repositories} repositórios.
      </p>
    </>
  );
}
