"use client";

import Link from "next/link";
import { use } from "react";
import { ArtifactBrowser } from "@/components/artifacts";
import { Button, ErrorBox, PageHeader, Spinner, Status } from "@/components/ui";
import { api, fmtDate, Repository, Task } from "@/lib/api";
import { useAction, useApi } from "@/lib/hooks";

export default function RepositoryPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const repo = useApi<Repository>(`/repositories/${id}`, { poll: 5000 });
  const action = useAction();
  if (!repo.data) return repo.error ? <ErrorBox error={repo.error} /> : <Spinner />;
  const r = repo.data;
  const start = (workflow: string, force = false) => action.run(async () => {
    const task = await api<Task>(`/repositories/${id}/analyze`, { method: "POST", json: { workflow, force } });
    window.location.href = `/tasks/${task.id}`;
  });
  const remove = () => action.run(async () => {
    if (!confirm("Solicitar remoção do repositório e relatórios? Uma aprovação será criada.")) return;
    await api(`/repositories/${id}`, { method: "DELETE" });
    window.location.href = "/approvals";
  });
  return (
    <>
      <PageHeader title={r.name}
        subtitle={<>{r.source_url} · commit <code>{r.commit_sha?.slice(0, 10) ?? "—"}</code> · <Status value={r.status} /> · {fmtDate(r.updated_at)}</>}
        actions={<>
          {r.last_task_id && <Link href={`/tasks/${r.last_task_id}`} className="rounded-md border border-line px-3 py-1.5 text-sm">Última execução</Link>}
          <Button variant="secondary" onClick={() => start("analyze_repository")} disabled={action.busy}>Analisar</Button>
          <Button variant="secondary" onClick={() => start("analyze_repository", true)} disabled={action.busy}>Reanalisar (ignorar cache)</Button>
          <Button variant="secondary" onClick={() => start("ingest_knowledge")} disabled={action.busy}>Indexar catálogo</Button>
          <Button variant="ghost" className="text-danger" onClick={remove} disabled={action.busy}>Remover</Button>
        </>} />
      <ErrorBox error={action.error} />
      <p className="mb-4 text-xs text-muted">Autorização declarada: {r.authorization_note}</p>
      <ArtifactBrowser path={`/repositories/${id}/artifacts`} />
    </>
  );
}
