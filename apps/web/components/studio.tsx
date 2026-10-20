"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { api, Artifact, fmtDate, Page, Project, Task } from "@/lib/api";
import { useAction, useApi } from "@/lib/hooks";
import { Button, Card, cx, Empty, ErrorBox, Markdown, Status, Textarea } from "./ui";

type FileEntry = { path: string; size: number };
type Commit = { sha: string; author: string; date: string; message: string; stat: string };

export function Studio({ project, onWorkflow }: { project: Project; onWorkflow: () => void }) {
  const files = useApi<{ head: string | null; files: FileEntry[] }>(`/projects/${project.id}/files`, { poll: 8000 });
  const history = useApi<{ commits: Commit[] }>(`/projects/${project.id}/history`, { poll: 8000 });
  const tasks = useApi<Page<Task>>(`/projects/${project.id}/tasks?limit=1`, { poll: 4000 });
  const tests = useApi<Page<Artifact>>(`/projects/${project.id}/artifacts?kind=test_log&limit=1`, { poll: 8000 });
  const [selected, setSelected] = useState<string | null>(null);
  const [content, setContent] = useState("");
  const [original, setOriginal] = useState("");
  const [diff, setDiff] = useState<{ sha: string; text: string } | null>(null);
  const [instructions, setInstructions] = useState("");
  const action = useAction();

  useEffect(() => {
    if (!selected) return;
    api<string>(`/projects/${project.id}/files/content?path=${encodeURIComponent(selected)}`)
      .then((t) => { setContent(t); setOriginal(t); })
      .catch((e) => { setContent(""); setOriginal(""); action.setError((e as Error).message); });
  }, [selected, project.id]); // eslint-disable-line react-hooks/exhaustive-deps

  const latest = tasks.data?.items[0];
  const latestDetail = useApi<{ steps: Task[] }>(latest ? `/tasks/${latest.id}` : null, { poll: 4000 });
  const testArtifact = tests.data?.items[0];
  const testDetail = useApi<Artifact>(testArtifact ? `/artifacts/${testArtifact.id}` : null);

  const tree = useMemo(() => files.data?.files ?? [], [files.data]);
  const save = () => action.run(async () => {
    await api(`/projects/${project.id}/files/content`, { method: "PUT", json: { path: selected, content } });
    setOriginal(content);
    files.reload();
    history.reload();
  });
  const showDiff = (sha: string) => action.run(async () => setDiff({ sha, text: await api<string>(`/projects/${project.id}/history/${sha}`) }));
  const startDevelop = () => action.run(async () => {
    await api(`/projects/${project.id}/workflows`, { method: "POST", json: { workflow: "develop", instructions } });
    setInstructions("");
    tasks.reload();
    onWorkflow();
  });
  const runTests = () => action.run(async () => {
    await api(`/projects/${project.id}/workflows`, { method: "POST", json: { workflow: "test" } });
    tasks.reload();
    onWorkflow();
  });

  return (
    <div className="space-y-4">
      <ErrorBox error={action.error} />
      <div className="grid gap-4 lg:grid-cols-[1fr_320px]">
        <Card title="Instruções para o Agente de Desenvolvimento">
          <Textarea rows={3} value={instructions} onChange={(e) => setInstructions(e.target.value)}
            placeholder={project.approved_plan_artifact_id ? "Opcional: descreva o próximo incremento (por padrão, o escopo do plano aprovado)." : "Aprove um plano na aba Visão geral para habilitar o desenvolvimento."} />
          <div className="mt-2 flex flex-wrap gap-2">
            <Button onClick={startDevelop} disabled={action.busy || !project.approved_plan_artifact_id}>Gerar código + testar</Button>
            <Button variant="secondary" onClick={runTests} disabled={action.busy || tree.length === 0}>Executar testes no sandbox</Button>
          </div>
        </Card>
        <Card title="Painel de agentes" actions={latest && <Link className="text-xs text-accent underline" href={`/tasks/${latest.id}`}>detalhes</Link>}>
          {!latest ? <Empty>Nenhuma execução.</Empty> : (
            <div className="space-y-1.5 text-sm">
              <div className="flex justify-between"><span className="font-medium">{latest.title}</span><Status value={latest.status} /></div>
              {latestDetail.data?.steps.map((s) => (
                <div key={s.id} className="flex justify-between gap-2 text-xs"><span className="text-muted">{s.agent} · {s.title}</span><Status value={s.status} /></div>
              ))}
            </div>
          )}
        </Card>
      </div>
      <div className="grid min-h-[420px] gap-4 lg:grid-cols-[240px_1fr]">
        <Card title={`Arquivos (${tree.length})`}>
          {tree.length === 0 ? <Empty>Workspace vazio.</Empty> : (
            <ul className="max-h-[480px] space-y-0.5 overflow-auto font-mono text-xs">
              {tree.map((f) => (
                <li key={f.path}>
                  <button onClick={() => { setSelected(f.path); setDiff(null); }} className={cx("w-full truncate rounded px-1.5 py-1 text-left", selected === f.path ? "bg-subtle font-semibold" : "hover:bg-subtle")} title={f.path}>
                    {f.path}
                  </button>
                </li>
              ))}
            </ul>
          )}
        </Card>
        <Card title={diff ? `Diff ${diff.sha.slice(0, 10)}` : selected ?? "Editor"}
          actions={diff ? <Button variant="secondary" onClick={() => setDiff(null)}>Fechar diff</Button> : selected && <Button onClick={save} disabled={action.busy || content === original}>Salvar (commit)</Button>}>
          {diff ? (
            <pre className="max-h-[520px] overflow-auto text-xs">{diff.text.split("\n").map((line, i) => (
              <div key={i} className={line.startsWith("+") && !line.startsWith("+++") ? "text-ok" : line.startsWith("-") && !line.startsWith("---") ? "text-danger" : ""}>{line || " "}</div>
            ))}</pre>
          ) : selected ? (
            <textarea aria-label={`Conteúdo de ${selected}`} value={content} onChange={(e) => setContent(e.target.value)} spellCheck={false}
              className="h-[480px] w-full resize-y rounded-md border border-line bg-subtle p-3 font-mono text-xs outline-none focus:border-accent" />
          ) : <Empty>Selecione um arquivo para visualizar ou editar.</Empty>}
        </Card>
      </div>
      <div className="grid gap-4 lg:grid-cols-2">
        <Card title="Histórico de alterações (Git)">
          {!history.data?.commits.length ? <Empty>Sem commits.</Empty> : (
            <ul className="max-h-80 divide-y divide-line overflow-auto text-sm">
              {history.data.commits.map((c) => (
                <li key={c.sha} className="py-2">
                  <button className="text-left hover:underline" onClick={() => showDiff(c.sha)}>{c.message}</button>
                  <p className="text-xs text-muted"><code>{c.sha.slice(0, 10)}</code> · {c.author} · {fmtDate(c.date)} {c.stat && `· ${c.stat}`}</p>
                </li>
              ))}
            </ul>
          )}
        </Card>
        <Card title="Resultados dos testes">
          {!testDetail.data ? <Empty>Nenhuma execução de testes ainda.</Empty> : (
            <div className="max-h-80 overflow-auto"><Markdown>{testDetail.data.content ?? ""}</Markdown></div>
          )}
        </Card>
      </div>
    </div>
  );
}
