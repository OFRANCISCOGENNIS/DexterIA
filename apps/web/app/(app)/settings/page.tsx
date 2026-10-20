"use client";

import { useState } from "react";
import { ThemeToggle } from "@/components/shell";
import { Button, Card, ErrorBox, Field, Input, PageHeader, Select, Spinner } from "@/components/ui";
import { api } from "@/lib/api";
import { useAction, useApi } from "@/lib/hooks";

type Integrations = {
  ai: { provider: string; configured: boolean; model: string; effort?: string; reason?: string; key_source?: string; supported_models: string[];
    effort_levels: string[]; pricing_per_mtok: Record<string, { input: number; output: number }>; default_budget_usd: number; refusal_fallbacks?: boolean };
  sandbox: { available: boolean; backend: string | null; reason: string | null; namespace_mode: string | null; docker: boolean; timeout_seconds: number; memory_mb: number };
  rea: { available: boolean; version?: string; reason?: string };
  git: { allowed_hosts: string[]; local_import_roots: string[]; max_repo_mb: number };
  pending: { name: string; status: string; detail: string }[];
};

export default function SettingsPage() {
  const { data, reload } = useApi<Integrations>("/integrations");
  const [form, setForm] = useState({ api_key: "", model: "", effort: "" });
  const action = useAction();
  if (!data) return <Spinner />;
  const save = () => action.run(async () => {
    await api("/integrations/ai", { method: "PUT", json: { api_key: form.api_key || null, model: form.model || null, effort: form.effort || null } });
    setForm({ api_key: "", model: "", effort: "" });
    reload();
  });
  const removeKey = () => action.run(async () => { await api("/integrations/ai/key", { method: "DELETE" }); reload(); });
  return (
    <>
      <PageHeader title="Configurações" actions={<ThemeToggle />} />
      <div className="grid gap-4 lg:grid-cols-2">
        <Card title="Provedor de IA (Anthropic)">
          <p className={`mb-3 text-sm ${data.ai.configured ? "text-ok" : "text-warn"}`}>
            {data.ai.configured ? `Configurado · modelo ${data.ai.model} · esforço ${data.ai.effort} · chave via ${data.ai.key_source}` : data.ai.reason}
          </p>
          <div className="space-y-3">
            <Field label="Chave de API" hint="Armazenada cifrada (Fernet) e nunca devolvida pela API. A variável ANTHROPIC_API_KEY também é aceita.">
              <Input type="password" autoComplete="off" value={form.api_key} onChange={(e) => setForm({ ...form, api_key: e.target.value })} placeholder="sk-ant-…" />
            </Field>
            <div className="grid grid-cols-2 gap-3">
              <Field label="Modelo">
                <Select className="w-full" value={form.model} onChange={(e) => setForm({ ...form, model: e.target.value })}>
                  <option value="">(manter {data.ai.model})</option>
                  {data.ai.supported_models.map((m) => <option key={m} value={m}>{m} — US$ {data.ai.pricing_per_mtok[m].input}/{data.ai.pricing_per_mtok[m].output} por MTok</option>)}
                </Select>
              </Field>
              <Field label="Esforço">
                <Select className="w-full" value={form.effort} onChange={(e) => setForm({ ...form, effort: e.target.value })}>
                  <option value="">(manter)</option>
                  {data.ai.effort_levels.map((e) => <option key={e} value={e}>{e}</option>)}
                </Select>
              </Field>
            </div>
            <ErrorBox error={action.error} />
            <div className="flex gap-2">
              <Button onClick={save} disabled={action.busy || (!form.api_key && !form.model && !form.effort)}>Salvar</Button>
              <Button variant="secondary" onClick={removeKey} disabled={action.busy}>Remover chave salva</Button>
            </div>
            <p className="text-xs text-muted">Orçamento padrão por projeto: US$ {data.ai.default_budget_usd}. Fallback em recusas: {data.ai.refusal_fallbacks ? "ativado" : "desativado"}.</p>
          </div>
        </Card>
        <Card title="Execução isolada (sandbox)">
          <dl className="space-y-1 text-sm">
            <div className="flex justify-between"><dt className="text-muted">Disponível</dt><dd className={data.sandbox.available ? "text-ok" : "text-danger"}>{data.sandbox.available ? "sim" : "não"}</dd></div>
            <div className="flex justify-between"><dt className="text-muted">Backend</dt><dd>{data.sandbox.backend ?? "—"}{data.sandbox.namespace_mode && ` (${data.sandbox.namespace_mode})`}</dd></div>
            <div className="flex justify-between"><dt className="text-muted">Rede</dt><dd>desabilitada por padrão</dd></div>
            <div className="flex justify-between"><dt className="text-muted">Limites</dt><dd>{data.sandbox.timeout_seconds}s · {data.sandbox.memory_mb} MB</dd></div>
            <div className="flex justify-between"><dt className="text-muted">Docker</dt><dd>{data.sandbox.docker ? "daemon ativo" : "indisponível"}</dd></div>
          </dl>
          {data.sandbox.reason && <p className="mt-2 text-xs text-danger">{data.sandbox.reason}</p>}
        </Card>
        <Card title="REA (engenharia reversa JS/TS)">
          <p className="text-sm">{data.rea.available ? `CLI rea ${data.rea.version} disponível — usada como adaptador na análise de repositórios JavaScript/TypeScript.` : data.rea.reason}</p>
        </Card>
        <Card title="Importação de repositórios">
          <p className="text-sm">Hosts Git permitidos: {data.git.allowed_hosts.join(", ")}</p>
          <p className="text-sm">Raízes locais autorizadas: {data.git.local_import_roots.length ? data.git.local_import_roots.join(", ") : "nenhuma (GENISIA_IMPORT_ROOTS)"}</p>
          <p className="text-sm">Tamanho máximo: {data.git.max_repo_mb} MB</p>
        </Card>
        <Card title="Integrações pendentes" className="lg:col-span-2">
          <ul className="space-y-2 text-sm">{data.pending.map((p) => <li key={p.name}><span className="font-medium">{p.name}</span> — {p.status}. <span className="text-muted">{p.detail}</span></li>)}</ul>
        </Card>
      </div>
    </>
  );
}
