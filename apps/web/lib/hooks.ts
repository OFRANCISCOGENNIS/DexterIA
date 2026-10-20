"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "./api";

/** Busca dados da API; com `poll` (ms) atualiza periodicamente enquanto `shouldPoll` for verdadeiro. */
export function useApi<T>(path: string | null, opts: { poll?: number; shouldPoll?: (data: T | null) => boolean } = {}) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const optsRef = useRef(opts);
  optsRef.current = opts;

  const reload = useCallback(async () => {
    if (!path) return;
    try {
      const result = await api<T>(path);
      setData(result);
      setError(null);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, [path]);

  useEffect(() => {
    setLoading(true);
    reload();
  }, [reload]);

  useEffect(() => {
    const { poll, shouldPoll } = optsRef.current;
    if (!poll) return;
    const id = setInterval(() => {
      if (!shouldPoll || shouldPoll(dataRef.current)) reload();
    }, poll);
    return () => clearInterval(id);
  }, [reload]);

  const dataRef = useRef<T | null>(null);
  dataRef.current = data;

  return { data, error, loading, reload, setData };
}

/** Executa uma ação da API controlando estado de envio e erro. */
export function useAction() {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const run = useCallback(async <T,>(fn: () => Promise<T>): Promise<T | undefined> => {
    setBusy(true);
    setError(null);
    try {
      return await fn();
    } catch (e) {
      setError((e as Error).message);
      return undefined;
    } finally {
      setBusy(false);
    }
  }, []);
  return { busy, error, run, setError };
}
