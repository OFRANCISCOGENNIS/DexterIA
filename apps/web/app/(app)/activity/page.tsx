"use client";

import { useState } from "react";
import { Button, PageHeader, Spinner } from "@/components/ui";
import { fmtDate, Page } from "@/lib/api";
import { useApi } from "@/lib/hooks";

type Event = { id: string; action: string; actor: string; project_id: string | null; target_type: string | null; target_id: string | null; details: Record<string, unknown>; created_at: string };

export default function ActivityPage() {
  const [offset, setOffset] = useState(0);
  const { data } = useApi<Page<Event>>(`/audit?limit=50&offset=${offset}`);
  return (
    <>
      <PageHeader title="Atividade" subtitle="Registro de auditoria verificável de ações e mudanças de estado." />
      {!data ? <Spinner /> : (
        <>
          <ul className="divide-y divide-line rounded-lg border border-line bg-panel text-sm">
            {data.items.map((e) => (
              <li key={e.id} className="flex flex-wrap justify-between gap-2 px-3 py-2">
                <span><code className="text-xs">{e.action}</code> <span className="text-muted">por {e.actor}</span>
                  {e.target_type && <span className="text-xs text-muted"> · {e.target_type} {e.target_id?.slice(0, 8)}</span>}
                  {Object.keys(e.details).length > 0 && <span className="ml-2 text-xs text-muted">{JSON.stringify(e.details).slice(0, 160)}</span>}</span>
                <span className="text-xs text-muted">{fmtDate(e.created_at)}</span>
              </li>
            ))}
          </ul>
          <div className="mt-3 flex items-center gap-2 text-xs text-muted">
            <Button variant="secondary" disabled={offset === 0} onClick={() => setOffset(Math.max(offset - 50, 0))}>Anterior</Button>
            <Button variant="secondary" disabled={offset + 50 >= data.total} onClick={() => setOffset(offset + 50)}>Próxima</Button>
            {data.total} eventos
          </div>
        </>
      )}
    </>
  );
}
