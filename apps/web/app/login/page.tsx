"use client";

import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";
import { ThemeToggle } from "@/components/shell";
import { Button, ErrorBox, Field, Input } from "@/components/ui";
import { api, setToken } from "@/lib/api";
import { useAction } from "@/lib/hooks";

export default function LoginPage() {
  const router = useRouter();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [form, setForm] = useState({ name: "", email: "", password: "" });
  const { busy, error, run } = useAction();

  const submit = (e: FormEvent) => {
    e.preventDefault();
    run(async () => {
      const body = mode === "login" ? { email: form.email, password: form.password } : form;
      const res = await api<{ access_token: string }>(`/auth/${mode}`, { method: "POST", json: body });
      setToken(res.access_token);
      router.replace("/");
    });
  };

  return (
    <div className="grid min-h-screen place-items-center p-4">
      <div className="absolute right-4 top-4"><ThemeToggle /></div>
      <div className="w-full max-w-sm rounded-xl border border-line bg-panel p-6 shadow-sm">
        <div className="mb-6 flex items-center gap-2">
          <span className="grid h-8 w-8 place-items-center rounded-md bg-accent text-sm font-bold text-white">G</span>
          <div>
            <h1 className="font-semibold">GENISIA AI</h1>
            <p className="text-xs text-muted">{mode === "login" ? "Entre na sua conta" : "Crie sua conta"}</p>
          </div>
        </div>
        <form onSubmit={submit} className="space-y-4">
          {mode === "register" && (
            <Field label="Nome"><Input required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} autoComplete="name" /></Field>
          )}
          <Field label="E-mail"><Input type="email" required value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} autoComplete="email" /></Field>
          <Field label="Senha" hint={mode === "register" ? "Mínimo de 8 caracteres" : undefined}>
            <Input type="password" required minLength={mode === "register" ? 8 : 1} value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })}
              autoComplete={mode === "login" ? "current-password" : "new-password"} />
          </Field>
          <ErrorBox error={error} />
          <Button type="submit" disabled={busy} className="w-full">{busy ? "Aguarde…" : mode === "login" ? "Entrar" : "Criar conta"}</Button>
        </form>
        <button className="mt-4 w-full text-center text-sm text-muted hover:text-fg" onClick={() => setMode(mode === "login" ? "register" : "login")}>
          {mode === "login" ? "Não tem conta? Cadastre-se" : "Já tem conta? Entrar"}
        </button>
      </div>
    </div>
  );
}
