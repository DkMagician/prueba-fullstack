import type { Transaction, TransactionCreate, Summary, SummaryCreate } from './types';

async function http<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`/api${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...(init?.headers ?? {}),
    },
  });

  if (!res.ok) {
    const text = await res.text().catch(() => '');
    throw new Error(`HTTP ${res.status} ${res.statusText} - ${text}`);
  }

  return res.json() as Promise<T>;
}

export const api = {
  listTransactions: () => http<Transaction[]>('/transactions'),
  createAsync: (payload: TransactionCreate, idempotencyKey?: string) =>
    http<Transaction>('/transactions/async-process', {
      method: 'POST',
      headers: idempotencyKey ? { 'Idempotency-Key': idempotencyKey } : undefined,
      body: JSON.stringify(payload),
    }),
  createSync: (payload: TransactionCreate, idempotencyKey?: string) =>
    http<Transaction>('/transactions/create', {
      method: 'POST',
      headers: idempotencyKey ? { 'Idempotency-Key': idempotencyKey } : undefined,
      body: JSON.stringify(payload),
    }),

  listSummaries: () => http<Summary[]>('/summaries'),
  getSummary: (id: string) => http<Summary>(`/summaries/${id}`),
  createSummaryAsync: (payload: SummaryCreate, idempotencyKey?: string) =>
    http<Summary>('/summaries/async', {
      method: 'POST',
      headers: idempotencyKey ? { 'Idempotency-Key': idempotencyKey } : undefined,
      body: JSON.stringify(payload),
    }),
};

export function buildWsUrl(path: string): string {
  const proto = window.location.protocol === 'https:' ? 'wss' : 'ws';
  return `${proto}://${window.location.host}/ws${path}`;
}
