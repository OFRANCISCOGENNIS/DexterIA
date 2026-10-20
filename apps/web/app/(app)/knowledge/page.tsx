"use client";

import { KnowledgeSearch } from "@/components/knowledge";
import { Button, Card, Empty, PageHeader } from "@/components/ui";
import { api, fmtDate } from "@/lib/api";
import { useApi } from "@/lib/hooks";

type Source = { id: string; name: string; kind: string; origin_url: string | null; origin_commit: string | null; license: string | null; item_count: number; indexed_at: string | null; project_id: string | null };

export default function KnowledgePage() {
  const sources = useApi<Source[]>("/knowledge/sources");
  const remove = async (s: Source) => {
    if (!confirm(`Remover a fonte "${s.name}" e seus ${s.item_count} itens indexados?`)) return;
    await api(`/knowledge/sources/${s.id}`, { method: "DELETE" });
    sources.reload();
  };
  return (
    <>
      <PageHeader title="Base de conhecimento" subtitle="Busca textual (full-text no PostgreSQL) sobre referências indexadas. Cada item mantém a fonte, o arquivo de origem e a licença." />
      <div className="grid gap-6 xl:grid-cols-[1fr_340px]">
        <KnowledgeSearch types={[{ value: "tool", label: "Ferramentas" }, { value: "api", label: "APIs" }, { value: "book", label: "Livros e cursos" },
          { value: "tutorial", label: "Tutoriais" }, { value: "resource", label: "Recursos" }, { value: "decision", label: "Decisões de projeto" }, { value: "memory", label: "Memória de projeto" }]} />
        <Card title="Fontes indexadas">
          {!sources.data?.length ? <Empty>Nenhuma fonte.</Empty> : (
            <ul className="space-y-3 text-sm">
              {sources.data.map((s) => (
                <li key={s.id}>
                  <div className="flex justify-between gap-2"><span className="font-medium">{s.name}</span>
                    {!s.project_id && <Button variant="ghost" className="px-1 py-0 text-xs text-danger" onClick={() => remove(s)}>remover</Button>}</div>
                  <p className="text-xs text-muted">{s.kind} · {s.item_count.toLocaleString("pt-BR")} itens · licença {s.license ?? "desconhecida"}
                    {s.origin_commit && <> · commit <code>{s.origin_commit.slice(0, 8)}</code></>} · {fmtDate(s.indexed_at)}</p>
                </li>
              ))}
            </ul>
          )}
        </Card>
      </div>
    </>
  );
}
