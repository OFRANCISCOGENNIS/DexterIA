"use client";

import { ArtifactBrowser } from "@/components/artifacts";
import { PageHeader } from "@/components/ui";

export default function ArchitecturePage() {
  return (
    <>
      <PageHeader title="Arquitetura" subtitle="Planos gerados pelo Agente Arquiteto: requisitos, componentes (diagrama Mermaid), dados, APIs, riscos, tarefas e critérios de aceitação." />
      <ArtifactBrowser path="/artifacts?kind=plan&limit=100" />
    </>
  );
}
