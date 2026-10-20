"use client";

import Link from "next/link";
import { Empty, PageHeader, Spinner, Status } from "@/components/ui";
import { fmtDate, Page, Project } from "@/lib/api";
import { useApi } from "@/lib/hooks";

export default function StudioIndex() {
  const { data } = useApi<Page<Project>>("/projects?limit=100");
  return (
    <>
      <PageHeader title="Studio de IA" subtitle="Escolha um projeto para abrir a área de desenvolvimento: instruções, árvore de arquivos, editor, histórico Git com diffs, resultados de testes e painel de agentes." />
      {!data ? <Spinner /> : !data.items.length ? <Empty>Crie um projeto para começar. <Link className="text-accent underline" href="/projects?new=1">Novo projeto</Link></Empty> : (
        <ul className="divide-y divide-line rounded-lg border border-line bg-panel">
          {data.items.map((p) => (
            <li key={p.id} className="flex items-center justify-between gap-2 px-4 py-3 text-sm">
              <Link href={`/projects/${p.id}?tab=studio`} className="font-medium hover:underline">{p.name}</Link>
              <span className="flex items-center gap-2"><Status value={p.status} /><span className="text-xs text-muted">{fmtDate(p.updated_at)}</span></span>
            </li>
          ))}
        </ul>
      )}
    </>
  );
}
