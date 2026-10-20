"use client";

import Link from "next/link";
import { useState } from "react";
import { api, Approval, fmtDate } from "@/lib/api";
import { useAction } from "@/lib/hooks";
import { Button, ErrorBox, Input, Status } from "./ui";

const ACTIONS: Record<string, string> = {
  "plan.execute": "Executar plano (gerar e testar código)",
  "project.delete": "Excluir projeto",
  "repository.delete": "Remover repositório",
  "sandbox.network": "Liberar rede no sandbox",
};

export function ApprovalCard({ approval, onDone }: { approval: Approval; onDone: () => void }) {
  const [reason, setReason] = useState("");
  const { busy, error, run } = useAction();
  const decide = (approve: boolean) => run(async () => {
    await api(`/approvals/${approval.id}/decide`, { method: "POST", json: { approve, reason: reason || null } });
    onDone();
  });
  return (
    <div className="rounded-lg border border-warn/50 bg-warn/5 p-4">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <div className="text-sm font-semibold">{ACTIONS[approval.action] ?? approval.action}</div>
          <p className="mt-1 text-sm">{approval.description}</p>
          <p className="mt-1 text-xs text-muted">Solicitado por {approval.requested_by} · {fmtDate(approval.created_at)}
            {approval.payload?.plan_artifact_id && <> · <Link className="text-accent underline" href={`/artifacts/${approval.payload.plan_artifact_id}`}>revisar plano</Link></>}
            {approval.task_id && <> · <Link className="text-accent underline" href={`/tasks/${approval.task_id}`}>tarefa</Link></>}
          </p>
        </div>
        <Status value={approval.status} />
      </div>
      {approval.status === "pending" && (
        <div className="mt-3 flex flex-wrap gap-2">
          <Input className="max-w-sm" placeholder="Motivo (opcional)" value={reason} onChange={(e) => setReason(e.target.value)} />
          <Button onClick={() => decide(true)} disabled={busy}>Aprovar</Button>
          <Button variant="danger" onClick={() => decide(false)} disabled={busy}>Rejeitar</Button>
        </div>
      )}
      {approval.reason && <p className="mt-2 text-xs text-muted">Motivo: {approval.reason}</p>}
      <div className="mt-2"><ErrorBox error={error} /></div>
    </div>
  );
}
