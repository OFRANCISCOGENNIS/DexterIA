"use client";

import { useEffect, useState } from "react";
import { api, KnowledgeItem, Page } from "@/lib/api";
import { useApi } from "@/lib/hooks";
import { Button, Empty, ErrorBox, Input, Select, Spinner } from "./ui";

type Filters = { item_type?: string; types?: { value: string; label: string }[]; showAuth?: boolean };

export function KnowledgeSearch({ item_type, types, showAuth }: Filters) {
  const [q, setQ] = useState("");
  const [type, setType] = useState(item_type ?? "");
  const [category, setCategory] = useState("");
  const [auth, setAuth] = useState("");
  const [match, setMatch] = useState("all");
  const [offset, setOffset] = useState(0);
  const [result, setResult] = useState<Page<KnowledgeItem> | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const cats = useApi<{ category: string; count: number }[]>(`/knowledge/categories${type ? `?item_type=${type}` : ""}`);

  const search = async (newOffset = 0) => {
    setLoading(true);
    const params = new URLSearchParams({ q, limit: "25", offset: String(newOffset), match });
    if (type) params.set("item_type", type);
    if (category) params.set("category", category);
    if (auth) params.set("auth", auth);
    try {
      setResult(await api<Page<KnowledgeItem>>(`/knowledge/search?${params}`));
      setOffset(newOffset);
      setError(null);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  };
  useEffect(() => { search(0); }, [type, category, auth, match]); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div>
      <form onSubmit={(e) => { e.preventDefault(); search(0); }} className="mb-4 flex flex-wrap gap-2">
        <Input className="max-w-md flex-1" value={q} onChange={(e) => setQ(e.target.value)} placeholder="Pesquisar (ex.: autenticação, banco de dados, react)…" aria-label="Termo de busca" />
        {types && (
          <Select value={type} onChange={(e) => { setType(e.target.value); setCategory(""); }} aria-label="Tipo">
            <option value="">Todos os tipos</option>
            {types.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
          </Select>
        )}
        <Select value={category} onChange={(e) => setCategory(e.target.value)} aria-label="Categoria" className="max-w-56">
          <option value="">Todas as categorias</option>
          {cats.data?.map((c) => <option key={c.category} value={c.category}>{c.category.slice(0, 50)} ({c.count})</option>)}
        </Select>
        {showAuth && (
          <Select value={auth} onChange={(e) => setAuth(e.target.value)} aria-label="Autenticação">
            <option value="">Qualquer autenticação</option>
            <option value="none">Sem autenticação</option>
            <option value="apikey">apiKey</option>
            <option value="oauth">OAuth</option>
          </Select>
        )}
        <Select value={match} onChange={(e) => setMatch(e.target.value)} aria-label="Correspondência">
          <option value="all">Todos os termos</option>
          <option value="any">Qualquer termo</option>
        </Select>
        <Button type="submit">Buscar</Button>
      </form>
      <ErrorBox error={error} />
      {loading && !result ? <Spinner /> : !result || result.items.length === 0 ? (
        <Empty>Nenhum resultado. Se a base estiver vazia, indexe um catálogo em Engenharia reversa → “Indexar catálogo”.</Empty>
      ) : (
        <>
          <p className="mb-2 text-xs text-muted">{result.total.toLocaleString("pt-BR")} resultado(s)</p>
          <ul className="divide-y divide-line rounded-lg border border-line bg-panel">
            {result.items.map((i) => (
              <li key={i.id} className="px-4 py-3">
                <div className="flex flex-wrap items-baseline justify-between gap-2">
                  <a href={i.url ?? "#"} target="_blank" rel="noreferrer noopener" className="font-medium text-accent hover:underline">{i.title}</a>
                  <span className="text-xs text-muted">{i.item_type}{i.category && ` · ${i.category}`}</span>
                </div>
                {i.description && <p className="mt-0.5 text-sm">{i.description}</p>}
                <p className="mt-1 text-xs text-muted">
                  Fonte: {i.source_name ?? "—"}{i.source_license && ` (${i.source_license})`}{i.origin_path && ` · ${i.origin_path}`}
                  {i.item_type === "api" && ` · auth: ${i.extra.auth} · HTTPS: ${i.extra.https ? "sim" : "não"} · CORS: ${i.extra.cors}`}
                </p>
              </li>
            ))}
          </ul>
          <div className="mt-3 flex gap-2">
            <Button variant="secondary" disabled={offset === 0} onClick={() => search(Math.max(offset - 25, 0))}>Anterior</Button>
            <Button variant="secondary" disabled={offset + 25 >= result.total} onClick={() => search(offset + 25)}>Próxima</Button>
          </div>
        </>
      )}
    </div>
  );
}
