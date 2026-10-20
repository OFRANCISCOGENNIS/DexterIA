"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { ReactNode, useEffect, useState } from "react";
import { api, getToken, setToken } from "@/lib/api";
import { cx } from "./ui";

const NAV = [
  { href: "/", label: "Dashboard" },
  { href: "/projects", label: "Projetos" },
  { href: "/studio", label: "Studio de IA" },
  { href: "/repositories", label: "Engenharia reversa" },
  { href: "/agents", label: "Agentes" },
  { href: "/automations", label: "Automações" },
  { href: "/apis", label: "APIs e ferramentas" },
  { href: "/architecture", label: "Arquitetura" },
  { href: "/learning", label: "Aprendizagem" },
  { href: "/knowledge", label: "Base de conhecimento" },
  { href: "/approvals", label: "Aprovações" },
  { href: "/activity", label: "Atividade" },
  { href: "/settings", label: "Configurações" },
];

export function ThemeToggle() {
  const [theme, setTheme] = useState<string>("light");
  useEffect(() => setTheme(document.documentElement.dataset.theme ?? "light"), []);
  const toggle = () => {
    const next = theme === "dark" ? "light" : "dark";
    document.documentElement.dataset.theme = next;
    try {
      localStorage.setItem("genisia.theme", next);
    } catch {
      /* ignora */
    }
    setTheme(next);
  };
  return (
    <button onClick={toggle} className="rounded-md px-2 py-1 text-xs text-muted hover:bg-subtle" aria-label="Alternar tema claro/escuro">
      {theme === "dark" ? "☀ Tema claro" : "☾ Tema escuro"}
    </button>
  );
}

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [user, setUser] = useState<{ name: string; email: string } | null>(null);
  const [open, setOpen] = useState(false);
  const [pending, setPending] = useState(0);

  useEffect(() => {
    if (!getToken()) {
      router.replace("/login");
      return;
    }
    api<{ name: string; email: string }>("/auth/me").then(setUser).catch(() => router.replace("/login"));
  }, [router]);

  useEffect(() => {
    if (!user) return;
    const load = () => api<{ total: number }>("/approvals?status_=pending&limit=1").then((r) => setPending(r.total)).catch(() => {});
    load();
    const id = setInterval(load, 10000);
    return () => clearInterval(id);
  }, [user, pathname]);

  useEffect(() => setOpen(false), [pathname]);

  if (!user) return <div className="p-8 text-sm text-muted">Carregando…</div>;

  const isActive = (href: string) => (href === "/" ? pathname === "/" : pathname.startsWith(href));
  return (
    <div className="flex min-h-screen">
      <aside className={cx("fixed inset-y-0 left-0 z-30 w-60 shrink-0 border-r border-line bg-panel transition-transform md:static md:translate-x-0", open ? "translate-x-0" : "-translate-x-full")}>
        <div className="flex h-14 items-center gap-2 border-b border-line px-4">
          <span className="grid h-7 w-7 place-items-center rounded-md bg-accent text-xs font-bold text-white">G</span>
          <span className="font-semibold tracking-tight">GENISIA AI</span>
        </div>
        <nav className="space-y-0.5 p-2" aria-label="Navegação principal">
          {NAV.map((item) => (
            <Link key={item.href} href={item.href} className={cx("flex items-center justify-between rounded-md px-3 py-1.5 text-sm", isActive(item.href) ? "bg-subtle font-medium" : "text-muted hover:bg-subtle hover:text-fg")}>
              {item.label}
              {item.href === "/approvals" && pending > 0 && <span className="rounded-full bg-warn px-1.5 text-xs text-white">{pending}</span>}
            </Link>
          ))}
        </nav>
      </aside>
      {open && <div className="fixed inset-0 z-20 bg-black/30 md:hidden" onClick={() => setOpen(false)} />}
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-14 items-center justify-between gap-2 border-b border-line bg-panel px-4">
          <button className="rounded-md px-2 py-1 text-sm hover:bg-subtle md:hidden" onClick={() => setOpen(true)} aria-label="Abrir menu">☰</button>
          <div className="hidden text-sm text-muted md:block">Desenvolvimento assistido por agentes, com execução isolada e aprovação humana</div>
          <div className="flex items-center gap-2">
            <ThemeToggle />
            <span className="hidden text-sm sm:inline">{user.name}</span>
            <button className="rounded-md px-2 py-1 text-xs text-muted hover:bg-subtle" onClick={() => { setToken(null); router.replace("/login"); }}>Sair</button>
          </div>
        </header>
        <main className="mx-auto w-full max-w-7xl flex-1 p-4 md:p-6">{children}</main>
      </div>
    </div>
  );
}
