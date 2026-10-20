"use client";

import { useState } from "react";
import { ApprovalCard } from "@/components/approvals";
import { Empty, PageHeader, Select, Spinner } from "@/components/ui";
import { Approval, Page } from "@/lib/api";
import { useApi } from "@/lib/hooks";

export default function ApprovalsPage() {
  const [status, setStatus] = useState("pending");
  const { data, reload } = useApi<Page<Approval>>(`/approvals?limit=100${status ? `&status_=${status}` : ""}`, { poll: 4000 });
  return (
    <>
      <PageHeader title="Aprovações" subtitle="Ações sensíveis (executar código gerado, excluir dados, liberar rede) só acontecem após sua decisão."
        actions={<Select value={status} onChange={(e) => setStatus(e.target.value)} aria-label="Filtrar">
          <option value="pending">Pendentes</option><option value="approved">Aprovadas</option><option value="rejected">Rejeitadas</option><option value="">Todas</option>
        </Select>} />
      {!data ? <Spinner /> : !data.items.length ? <Empty>Nada por aqui.</Empty> : (
        <div className="space-y-3">{data.items.map((a) => <ApprovalCard key={a.id} approval={a} onDone={reload} />)}</div>
      )}
    </>
  );
}
