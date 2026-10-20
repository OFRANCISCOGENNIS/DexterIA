// Cliente HTTP mínimo para a API do GENISIA AI.
const TOKEN_KEY = "genisia.token";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

export function getToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

export function setToken(token: string | null) {
  try {
    if (token) localStorage.setItem(TOKEN_KEY, token);
    else localStorage.removeItem(TOKEN_KEY);
  } catch {
    /* armazenamento indisponível */
  }
}

export async function api<T = unknown>(path: string, init: RequestInit & { json?: unknown } = {}): Promise<T> {
  const headers = new Headers(init.headers);
  const token = getToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  let body = init.body;
  if (init.json !== undefined) {
    headers.set("Content-Type", "application/json");
    body = JSON.stringify(init.json);
  }
  const res = await fetch(`/api${path}`, { ...init, headers, body });
  if (res.status === 401 && typeof window !== "undefined" && !path.startsWith("/auth/")) {
    setToken(null);
    window.location.href = "/login";
  }
  const text = await res.text();
  if (!res.ok) {
    let message = text || res.statusText;
    try {
      const data = JSON.parse(text);
      message = typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail);
      if (data.errors?.length) message += ": " + data.errors.map((e: { loc: string[]; msg: string }) => `${e.loc.slice(1).join(".")} ${e.msg}`).join("; ");
    } catch {
      /* resposta não-JSON */
    }
    throw new ApiError(res.status, message);
  }
  const type = res.headers.get("content-type") ?? "";
  return (type.includes("application/json") ? JSON.parse(text || "null") : text) as T;
}

export type Page<T> = { items: T[]; total: number; limit: number; offset: number };

export type Project = {
  id: string;
  name: string;
  description: string;
  requirements: string;
  language: string;
  stack: string[];
  settings: { ai_budget_usd: number; max_fix_iterations: number; sandbox_network: boolean };
  status: string;
  approved_plan_artifact_id: string | null;
  created_at: string;
  updated_at: string;
  stats?: { workflows_by_status: Record<string, number>; ai_cost_usd: number; input_tokens: number; output_tokens: number; pending_approvals: number; budget_usd: number };
};

export type Task = {
  id: string;
  project_id: string | null;
  parent_id: string | null;
  kind: string;
  step_key: string | null;
  agent: string | null;
  title: string;
  objective: string;
  status: string;
  depends_on: string[];
  input: Record<string, unknown>;
  result: Record<string, any> | null;
  error: string | null;
  optional: boolean;
  attempts: number;
  max_attempts: number;
  cancel_requested: boolean;
  started_at: string | null;
  finished_at: string | null;
  created_at: string;
};

export type AgentRun = {
  id: string;
  task_id: string;
  agent: string;
  attempt: number;
  status: string;
  started_at: string;
  finished_at: string | null;
  provider: string | null;
  model: string | null;
  input_tokens: number;
  output_tokens: number;
  cost_usd: number;
  summary: string | null;
  error: string | null;
  logs: string;
};

export type Approval = {
  id: string;
  project_id: string | null;
  task_id: string | null;
  action: string;
  description: string;
  payload: Record<string, any>;
  status: string;
  requested_by: string;
  decided_at: string | null;
  reason: string | null;
  created_at: string;
};

export type TaskDetail = Task & { steps: Task[]; runs: AgentRun[]; approvals: Approval[] };

export type Artifact = {
  id: string;
  project_id: string | null;
  repository_id: string | null;
  task_id: string | null;
  kind: string;
  title: string;
  content_type: string;
  created_at: string;
  content?: string;
  data?: Record<string, any> | null;
};

export type Repository = {
  id: string;
  name: string;
  source_type: string;
  source_url: string;
  ref: string | null;
  commit_sha: string | null;
  status: string;
  authorization_note: string;
  last_task_id: string | null;
  last_analysis_artifact_id: string | null;
  summary: Record<string, any> | null;
  created_at: string;
  updated_at: string;
};

export type KnowledgeItem = {
  id: string;
  title: string;
  url: string | null;
  description: string;
  category: string;
  item_type: string;
  tags: string[];
  extra: Record<string, any>;
  source_id: string;
  source_name: string | null;
  source_license: string | null;
  origin_path: string | null;
  score: number | null;
  created_at: string | null;
};

export const ACTIVE = ["queued", "running", "awaiting_approval", "pending"];

export function fmtDate(value: string | null | undefined) {
  if (!value) return "—";
  return new Date(value).toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "short" });
}

export function usd(value: number | undefined) {
  return `US$ ${(value ?? 0).toFixed(4)}`;
}
