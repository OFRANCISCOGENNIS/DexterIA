"use client";

import Link from "next/link";
import { use, useState } from "react";
import { ApprovalCard } from "@/components/approvals";
import { Button, Card, cx, ErrorBox, PageHeader, Spinner, Status } from "@/components/ui";
import { ACTIVE, api, fmtDate, TaskDetail, usd } from "@/lib/api";
import { useAction, useApi } from "@/lib/hooks";

export default function TaskPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const { data, error, reload } = useApi<TaskDetail>(`/tasks/${id}`, { poll: 2000, shouldPoll: (d) => !d || ACTIVE.includes(d.status) });
  const action = useAction();
  const [openRun, setOpenRun] = useState<string | null>(null);
  if (!data) return error ? <ErrorBox error={error} /> : <Spinner />;
  const titleById = Object.fromEntries(data.steps.map((s) => [s.id, s.title]));
  const cost = data.runs.reduce((acc, r) => acc + r.cost_usd, 0);
  const tokens = data.runs.reduce((acc, r) => acc + r.input_tokens + r.output_tokens, 0);
  const active = ACTIVE.includes(data.status);
  const cancel = () => action.run(async () => { await api(`/tasks/${id}/cancel`, { method: "POST" }); reload(); });
  const retry = () => action.run(async () => { await api(`/tasks/${id}/retry`, { method: "POST" }); reload(); });
  const duration = (a: string | null, b: string | null) => (a && b ? `${Math.round((new Date(b).getTime() - new Date(a).getTime()) / 100) / 10}s` : "—");
  return (
    <>
      <PageHeader title={data.title} subtitle={<>{data.objective} · <Status value={data.status} /> {data.cancel_requested && "· cancelamento solicitado"}</>}
        actions={<>
          {data.project_id && <Link href={`/projects/${data.project_id}`} className="rounded-md border border-line px-3 py-1.5 text-sm">Projeto</Link>}
          {typeof data.input.repository_id === "string" && <Link href={`/repositories/${data.input.repository_id}`} className="rounded-md border border-line px-3 py-1.5 text-sm">Repositório</Link>}
          {active && <Button variant="danger" onClick={cancel} disabled={action.busy}>Cancelar</Button>}
          {["failed", "cancelled"].includes(data.status) && <Button variant="secondary" onClick={retry} disabled={action.busy}>Retomar etapas pendentes</Button>}
        </>} />
      <ErrorBox error={action.error} />
      {data.error && <div className="mb-4"><ErrorBox error={data.error} /></div>}
      <div className="mb-4 space-y-3">
        {data.approvals.filter((a) => a.status === "pending").map((a) => <ApprovalCard key={a.id} approval={a} onDone={reload} />)}
      </div>
      <div className="grid gap-4 lg:grid-cols-[1fr_300px]">
        <Card title="Etapas e dependências">
          <ol className="space-y-2">
            {data.steps.map((s, i) => (
              <li key={s.id} className="rounded-md border border-line p-3">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="text-sm"><span className="mr-2 text-xs text-muted">{i + 1}.</span><span className="font-medium">{s.title}</span>
                    <span className="ml-2 rounded bg-subtle px-1.5 py-0.5 text-xs">{s.agent}</span>{s.optional && <span className="ml-1 text-xs text-muted">(opcional)</span>}</div>
                  <Status value={s.status} />
                </div>
                <p className="mt-1 text-xs text-muted">
                  {s.depends_on.length ? `Depende de: ${s.depends_on.map((d) => titleById[d]).join(", ")}` : "Sem dependências"} · tentativas {s.attempts}/{s.max_attempts} · duração {duration(s.started_at, s.finished_at)}
                </p>
                {s.error && <p className="mt-1 text-xs text-danger">{s.error}</p>}
                {s.result?.artifact_id && <Link className="mt-1 inline-block text-xs text-accent underline" href={`/artifacts/${s.result.artifact_id}`}>Ver resultado</Link>}
                {s.result?.plan_artifact_id && <Link className="mt-1 inline-block text-xs text-accent underline" href={`/artifacts/${s.result.plan_artifact_id}`}>Ver plano</Link>}
              </li>
            ))}
          </ol>
        </Card>
        <Card title="Resumo">
          <dl className="space-y-1 text-sm">
            <div className="flex justify-between"><dt className="text-muted">Criado</dt><dd>{fmtDate(data.created_at)}</dd></div>
            <div className="flex justify-between"><dt className="text-muted">Início</dt><dd>{fmtDate(data.started_at)}</dd></div>
            <div className="flex justify-between"><dt className="text-muted">Fim</dt><dd>{fmtDate(data.finished_at)}</dd></div>
            <div className="flex justify-between"><dt className="text-muted">Execuções de agentes</dt><dd>{data.runs.length}</dd></div>
            <div className="flex justify-between"><dt className="text-muted">Tokens de IA</dt><dd>{tokens.toLocaleString("pt-BR")}</dd></div>
            <div className="flex justify-between"><dt className="text-muted">Custo estimado</dt><dd>{usd(cost)}</dd></div>
          </dl>
        </Card>
      </div>
      <Card title="Execuções e logs" className="mt-4">
        <ul className="space-y-2">
          {data.runs.map((r) => (
            <li key={r.id} className="rounded-md border border-line">
              <button className="flex w-full flex-wrap items-center justify-between gap-2 px-3 py-2 text-left text-sm" onClick={() => setOpenRun(openRun === r.id ? null : r.id)} aria-expanded={openRun === r.id}>
                <span><span className="font-medium">{r.agent}</span> <span className="text-xs text-muted">tentativa {r.attempt} · {fmtDate(r.started_at)}
                  {r.model && ` · ${r.provider}/${r.model} · ${r.input_tokens + r.output_tokens} tokens · ${usd(r.cost_usd)}`}</span></span>
                <Status value={r.status} />
              </button>
              <pre className={cx("max-h-96 overflow-auto border-t border-line bg-subtle p-3 text-xs", openRun === r.id ? "block" : "hidden")}>{r.logs || "(sem logs)"}{r.error && `\nERRO: ${r.error}`}</pre>
            </li>
          ))}
          {!data.runs.length && <li className="text-sm text-muted">Nenhuma execução ainda.</li>}
        </ul>
      </Card>
    </>
  );
}
