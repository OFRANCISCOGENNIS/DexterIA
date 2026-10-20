"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { FormEvent, Suspense, useState } from "react";
import { Button, Card, Empty, ErrorBox, Field, Input, PageHeader, Select, Spinner, Status, Textarea } from "@/components/ui";
import { api, fmtDate, Page, Project } from "@/lib/api";
import { useAction, useApi } from "@/lib/hooks";

const EXAMPLE = "Quero desenvolver um sistema financeiro com dashboard, controle de despesas, metas e relatórios.";

function NewProject({ onCancel }: { onCancel: () => void }) {
  const router = useRouter();
  const [form, setForm] = useState({ name: "", description: "", requirements: "", language: "python", stack: "" });
  const { busy, error, run } = useAction();
  const submit = (e: FormEvent) => {
    e.preventDefault();
    run(async () => {
      const project = await api<Project>("/projects", {
        method: "POST",
        json: { ...form, stack: form.stack.split(",").map((s) => s.trim()).filter(Boolean) },
      });
      router.push(`/projects/${project.id}`);
    });
  };
  return (
    <Card title="Nova missão" className="mb-6">
      <form onSubmit={submit} className="grid gap-4 md:grid-cols-2">
        <Field label="Nome do projeto"><Input required maxLength={160} value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} /></Field>
        <div className="grid grid-cols-2 gap-3">
          <Field label="Linguagem">
            <Select value={form.language} onChange={(e) => setForm({ ...form, language: e.target.value })} className="w-full">
              <option value="python">Python</option>
              <option value="javascript">JavaScript (Node.js)</option>
            </Select>
          </Field>
          <Field label="Stack preferida" hint="Separada por vírgulas"><Input value={form.stack} onChange={(e) => setForm({ ...form, stack: e.target.value })} placeholder="fastapi, postgresql" /></Field>
        </div>
        <div className="md:col-span-2"><Field label="Descrição"><Input value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} /></Field></div>
        <div className="md:col-span-2">
          <Field label="Objetivo e requisitos" hint="Descreva o que o software deve fazer. O orquestrador extrai requisitos, riscos e critérios de aceitação.">
            <Textarea rows={5} value={form.requirements} placeholder={EXAMPLE} onChange={(e) => setForm({ ...form, requirements: e.target.value })} />
          </Field>
          <button type="button" className="mt-1 text-xs text-accent underline" onClick={() => setForm({ ...form, name: form.name || "Sistema financeiro", requirements: EXAMPLE })}>Usar exemplo</button>
        </div>
        <div className="md:col-span-2"><ErrorBox error={error} /></div>
        <div className="flex gap-2 md:col-span-2">
          <Button type="submit" disabled={busy}>{busy ? "Criando…" : "Criar projeto"}</Button>
          <Button type="button" variant="secondary" onClick={onCancel}>Cancelar</Button>
        </div>
      </form>
    </Card>
  );
}

function ProjectsInner() {
  const params = useSearchParams();
  const [creating, setCreating] = useState(params.get("new") === "1");
  const [q, setQ] = useState("");
  const { data, error, loading } = useApi<Page<Project>>(`/projects?limit=100${q ? `&q=${encodeURIComponent(q)}` : ""}`);
  return (
    <>
      <PageHeader title="Projetos" subtitle="Cada projeto tem requisitos, planos, um workspace Git isolado e histórico de execuções."
        actions={!creating && <Button onClick={() => setCreating(true)}>Novo projeto</Button>} />
      {creating && <NewProject onCancel={() => setCreating(false)} />}
      <div className="mb-3 max-w-xs"><Input placeholder="Filtrar por nome…" value={q} onChange={(e) => setQ(e.target.value)} aria-label="Filtrar projetos" /></div>
      <ErrorBox error={error} />
      {loading && !data ? <Spinner /> : data && data.items.length === 0 ? <Empty>Nenhum projeto encontrado.</Empty> : (
        <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
          {data?.items.map((p) => (
            <Link key={p.id} href={`/projects/${p.id}`} className="rounded-lg border border-line bg-panel p-4 hover:border-accent">
              <div className="flex items-start justify-between gap-2">
                <h3 className="font-medium">{p.name}</h3>
                <Status value={p.approved_plan_artifact_id && p.status === "approved" ? "approved_plan" : p.status} />
              </div>
              <p className="mt-1 line-clamp-2 text-sm text-muted">{p.description || p.requirements || "Sem descrição"}</p>
              <p className="mt-3 text-xs text-muted">{p.language} · atualizado {fmtDate(p.updated_at)}</p>
            </Link>
          ))}
        </div>
      )}
    </>
  );
}

export default function ProjectsPage() {
  return <Suspense fallback={<Spinner />}><ProjectsInner /></Suspense>;
}
