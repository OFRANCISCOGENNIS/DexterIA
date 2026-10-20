"use client";

import { KnowledgeSearch } from "@/components/knowledge";
import { PageHeader } from "@/components/ui";

export default function ApisPage() {
  return (
    <>
      <PageHeader title="APIs e ferramentas" subtitle="Catálogo de APIs (public-apis) e de ferramentas (awesome). Disponibilidade e gratuidade não são garantidas: confira sempre a documentação oficial antes de integrar." />
      <KnowledgeSearch item_type="api" showAuth types={[{ value: "api", label: "APIs" }, { value: "tool", label: "Ferramentas e bibliotecas" }]} />
    </>
  );
}
