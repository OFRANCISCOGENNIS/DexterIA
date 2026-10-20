"use client";

import { KnowledgeSearch } from "@/components/knowledge";
import { LearningPaths } from "@/components/learning";
import { PageHeader, Tabs } from "@/components/ui";

export default function LearningPage() {
  return (
    <>
      <PageHeader title="Aprendizagem" subtitle="Trilhas de estudo montadas a partir dos seus projetos ou objetivos, com progresso, e o catálogo de livros, cursos e tutoriais gratuitos. Apenas links e metadados são armazenados." />
      <Tabs tabs={[
        { key: "paths", label: "Minhas trilhas", content: <LearningPaths /> },
        { key: "catalog", label: "Catálogo", content: <KnowledgeSearch item_type="book" types={[{ value: "book", label: "Livros e cursos" }, { value: "tutorial", label: "Tutoriais (build-your-own-x)" }, { value: "resource", label: "Trilhas e materiais" }]} /> },
      ]} />
    </>
  );
}
