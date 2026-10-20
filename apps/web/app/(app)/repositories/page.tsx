"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import { Button, Card, Empty, ErrorBox, Field, Input, PageHeader, Select, Spinner, Status } from "@/components/ui";
import { api, fmtDate, getToken, Page, Repository, Task } from "@/lib/api";
import { useAction, useApi } from "@/lib/hooks";

export default function RepositoriesPage() {
  const list = useApi<Page<Repository>>("/repositories?limit=100", { poll: 5000 });
  const [form, setForm] = useState({ source_type: "git", source_url: "", ref: "", authorization_note: "", workflow: "analyze_repository" });
  const [file, setFile] = useState<File | null>(null);
  const action = useAction();

  const submit = (e: FormEvent) => {
    e.preventDefault();
    action.run(async () => {
      let repo: Repository;
      if (form.source_type === "upload") {
        if (!file) throw new Error("Selecione um arquivo .zip");
        const data = new FormData();
        data.append("file", file);
        data.append("authorization_note", form.authorization_note);
        const res = await fetch("/api/repositories/upload", { method: "POST", body: data, headers: { Authorization: `Bearer ${getToken()}` } });
        if (!res.ok) throw new Error((await res.json()).detail ?? "Falha no envio");
        repo = await res.json();
      } else {
        repo = await api<Repository>("/repositories", { method: "POST", json: { source_type: form.source_type, source_url: form.source_url, ref: form.ref || null, authorization_note: form.authorization_note } });
      }
      const task = await api<Task>(`/repositories/${repo.id}/analyze`, { method: "POST", json: { workflow: form.workflow } });
      window.location.href = `/tasks/${task.id}`;
    });
  };

  return (
    <>
      <PageHeader title="Engenharia reversa e Repository Intelligence"
        subtitle="Importe repositórios ou arquivos autorizados. A análise é estática (nada é executado) e separa fatos comprovados (✅) de hipóteses (🔎)." />
      <Card title="Importar e analisar" className="mb-6">
        <form onSubmit={submit} className="grid gap-4 md:grid-cols-2">
          <Field label="Origem">
            <Select className="w-full" value={form.source_type} onChange={(e) => setForm({ ...form, source_type: e.target.value })}>
              <option value="git">Repositório Git (HTTPS)</option>
              <option value="local">Diretório local autorizado</option>
              <option value="upload">Arquivo ZIP</option>
            </Select>
          </Field>
          {form.source_type === "upload" ? (
            <Field label="Arquivo .zip (até 100 MB)"><Input type="file" accept=".zip" onChange={(e) => setFile(e.target.files?.[0] ?? null)} /></Field>
          ) : (
            <Field label={form.source_type === "git" ? "URL" : "Caminho"} hint={form.source_type === "git" ? "Hosts permitidos: github.com, gitlab.com, bitbucket.org, codeberg.org" : "Deve estar dentro de GENISIA_IMPORT_ROOTS"}>
              <Input required value={form.source_url} onChange={(e) => setForm({ ...form, source_url: e.target.value })} placeholder={form.source_type === "git" ? "https://github.com/dono/repositorio" : "/caminho/do/projeto"} />
            </Field>
          )}
          {form.source_type === "git" && <Field label="Branch ou tag (opcional)"><Input value={form.ref} onChange={(e) => setForm({ ...form, ref: e.target.value })} /></Field>}
          <Field label="Fluxo">
            <Select className="w-full" value={form.workflow} onChange={(e) => setForm({ ...form, workflow: e.target.value })}>
              <option value="analyze_repository">Análise completa (estrutura, tecnologias, interfaces, segurança, otimização)</option>
              <option value="ingest_knowledge">Indexar catálogo (links/APIs/livros) na base de conhecimento</option>
            </Select>
          </Field>
          <div className="md:col-span-2">
            <Field label="Declaração de autorização" hint="Obrigatória. Analise apenas sistemas e arquivos que você tem autorização para inspecionar.">
              <Input required minLength={3} value={form.authorization_note} onChange={(e) => setForm({ ...form, authorization_note: e.target.value })} placeholder="Ex.: repositório público para estudo; ou código da minha empresa" />
            </Field>
          </div>
          <div className="md:col-span-2"><ErrorBox error={action.error} /></div>
          <div><Button type="submit" disabled={action.busy}>{action.busy ? "Enviando…" : "Importar e analisar"}</Button></div>
        </form>
      </Card>
      {!list.data ? <Spinner /> : !list.data.items.length ? <Empty>Nenhum repositório importado.</Empty> : (
        <div className="overflow-x-auto rounded-lg border border-line bg-panel">
          <table className="w-full text-sm">
            <thead className="bg-subtle text-left text-xs text-muted">
              <tr><th className="p-2">Repositório</th><th className="p-2">Status</th><th className="p-2">Tipo provável 🔎</th><th className="p-2">Linguagens</th><th className="p-2">Licença</th><th className="p-2">Atualizado</th></tr>
            </thead>
            <tbody>
              {list.data.items.map((r) => (
                <tr key={r.id} className="border-t border-line">
                  <td className="p-2"><Link className="font-medium hover:underline" href={`/repositories/${r.id}`}>{r.name}</Link><div className="text-xs text-muted">{r.source_url}</div></td>
                  <td className="p-2"><Status value={r.status} /></td>
                  <td className="p-2 text-xs">{(r.summary?.kinds ?? []).join(", ")}</td>
                  <td className="p-2 text-xs">{(r.summary?.languages ?? []).slice(0, 3).join(", ")}</td>
                  <td className="p-2 text-xs">{r.summary?.license ?? "—"}</td>
                  <td className="p-2 text-xs text-muted">{fmtDate(r.updated_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}
