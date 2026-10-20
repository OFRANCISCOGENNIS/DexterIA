"use client";

import Link from "next/link";
import { use } from "react";
import { Card, ErrorBox, Markdown, PageHeader, Spinner } from "@/components/ui";
import { Artifact, fmtDate } from "@/lib/api";
import { useApi } from "@/lib/hooks";

export default function ArtifactPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const { data, error } = useApi<Artifact>(`/artifacts/${id}`);
  if (!data) return error ? <ErrorBox error={error} /> : <Spinner />;
  const back = data.project_id ? `/projects/${data.project_id}?tab=artifacts` : data.repository_id ? `/repositories/${data.repository_id}` : "/";
  return (
    <>
      <PageHeader title={data.title} subtitle={`${data.kind} · ${fmtDate(data.created_at)}`} actions={<Link className="text-sm text-accent underline" href={back}>Voltar</Link>} />
      <Card><Markdown>{data.content ?? ""}</Markdown></Card>
    </>
  );
}
