"use client";

import Link from "next/link";
import { Card, Empty, PageHeader, Spinner, Status } from "@/components/ui";
import { AgentRun, fmtDate, Page, usd } from "@/lib/api";
import { useApi } from "@/lib/hooks";

type Agent = { name: string; title: string; description: string; responsibilities: string[]; uses_ai: boolean; state: string; running: number;
  stats: { runs: number; by_status: Record<string, number>; cost_usd: number; tokens: number } };

export default function AgentsPage() {
  const agents = useApi<Agent[]>("/agents", { poll: 4000 });
  const runs = useApi<Page<AgentRun>>("/agent-runs?limit=30", { poll: 4000 });
  return (
    <>
      <PageHeader title="Agentes" subtitle="Agentes especializados coordenados pelo orquestrador. Cada etapa recebe somente os resultados das etapas de que depende." />
      {!agents.data ? <Spinner /> : (
        <div className="mb-6 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          {agents.data.map((a) => (
            <div key={a.name} className="rounded-lg border border-line bg-panel p-4">
              <div className="flex items-start justify-between gap-2">
                <div><h3 className="font-medium">{a.title}</h3><code className="text-xs text-muted">{a.name}</code></div>
                <span className={`rounded-full px-2 py-0.5 text-xs ${a.running ? "bg-accent/15 text-accent" : "bg-subtle text-muted"}`}>{a.state}</span>
              </div>
              <p className="mt-2 text-sm text-muted">{a.description}</p>
              <ul className="mt-2 list-disc pl-4 text-xs text-muted">{a.responsibilities.map((r) => <li key={r}>{r}</li>)}</ul>
              <p className="mt-3 text-xs">{a.uses_ai ? "Usa IA" : "Determinístico (sem IA)"} · {a.stats.runs} execuções · {a.stats.tokens.toLocaleString("pt-BR")} tokens · {usd(a.stats.cost_usd)}</p>
              {Object.keys(a.stats.by_status).length > 0 && <p className="mt-1 flex flex-wrap gap-1">{Object.entries(a.stats.by_status).map(([s, n]) => <span key={s} className="text-xs"><Status value={s} /> {n}</span>)}</p>}
            </div>
          ))}
        </div>
      )}
      <Card title="Execuções recentes">
        {!runs.data?.items.length ? <Empty>Nenhuma execução.</Empty> : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="text-left text-xs text-muted"><tr><th className="p-2">Agente</th><th className="p-2">Status</th><th className="p-2">Início</th><th className="p-2">Modelo</th><th className="p-2">Tokens</th><th className="p-2">Custo</th><th className="p-2">Erro</th></tr></thead>
              <tbody>
                {runs.data.items.map((r) => (
                  <tr key={r.id} className="border-t border-line">
                    <td className="p-2"><Link className="hover:underline" href={`/tasks/${r.task_id}`}>{r.agent}</Link></td>
                    <td className="p-2"><Status value={r.status} /></td>
                    <td className="p-2 text-xs text-muted">{fmtDate(r.started_at)}</td>
                    <td className="p-2 text-xs">{r.model ?? "—"}</td>
                    <td className="p-2 text-xs">{r.input_tokens + r.output_tokens}</td>
                    <td className="p-2 text-xs">{usd(r.cost_usd)}</td>
                    <td className="max-w-xs truncate p-2 text-xs text-danger" title={r.error ?? ""}>{r.error}</td>
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
