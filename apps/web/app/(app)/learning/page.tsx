"use client";

import { KnowledgeSearch } from "@/components/knowledge";
import { PageHeader } from "@/components/ui";

export default function LearningPage() {
  return (
    <>
      <PageHeader title="Aprendizagem" subtitle="Livros e cursos gratuitos (free-programming-books), tutoriais de construção do zero (build-your-own-x) e trilhas de estudo (coding-interview-university, developer-roadmap, system-design-primer). Apenas links e metadados são armazenados." />
      <KnowledgeSearch item_type="book" types={[{ value: "book", label: "Livros e cursos" }, { value: "tutorial", label: "Tutoriais (build-your-own-x)" }, { value: "resource", label: "Trilhas e materiais" }]} />
    </>
  );
}
