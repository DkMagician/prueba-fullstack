import { useEffect, useMemo, useRef, useState } from 'react';
import './App.css';
import { api, buildWsUrl } from './api';
import type {
  Transaction,
  TransactionCreate,
  TxCreatedEvent,
  TxStatusUpdatedEvent,
  Summary,
  SummaryCreate,
  SummaryCreatedEvent,
  SummaryUpdatedEvent,
} from './types';

function nowKey(prefix = 'k'): string {
  return `${prefix}-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function safeJsonParse<T>(s: string): T | null {
  try {
    return JSON.parse(s) as T;
  } catch {
    return null;
  }
}

export default function App() {
  const [txs, setTxs] = useState<Transaction[]>([]);
  const [summaries, setSummaries] = useState<Summary[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [txForm, setTxForm] = useState<TransactionCreate>({
    user_id: 'u1',
    monto: 10.0,
    tipo: 'pago',
  });

  const [sumForm, setSumForm] = useState<SummaryCreate>({
    source: 'manual',
    text: 'Escribe aquí un texto para resumir...',
  });

  const wsRef = useRef<WebSocket | null>(null);
  const wsUrl = useMemo(() => buildWsUrl('/transactions/stream'), []);

  async function refreshAll() {
    setLoading(true);
    setError(null);
    try {
      const [txData, sumData] = await Promise.all([api.listTransactions(), api.listSummaries()]);
      setTxs(txData);
      setSummaries(sumData);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }

  async function refreshTransactionsOnly() {
    try {
      const txData = await api.listTransactions();
      setTxs(txData);
    } catch (e) {
      console.warn('Failed to refresh transactions', e);
    }
  }

  async function refreshSummariesOnly() {
    try {
      const sumData = await api.listSummaries();
      setSummaries(sumData);
    } catch (e) {
      console.warn('Failed to refresh summaries', e);
    }
  }

  useEffect(() => {
    refreshAll();
  }, []);

  useEffect(() => {
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => console.log('WS connected', wsUrl);

    ws.onmessage = (ev) => {
      const msg = typeof ev.data === 'string' ? ev.data : '';
      const base = safeJsonParse<{ event?: string }>(msg);
      if (!base?.event) return;

      // ---- TX CREATED (pendiente inmediato aunque venga de demo.sh/curl/Playwright) ----
      if (base.event === 'tx_created') {
        const parsed = safeJsonParse<TxCreatedEvent>(msg);
        if (!parsed) return;

        const tx: Transaction = {
          id: parsed.id,
          user_id: parsed.user_id,
          monto: parsed.monto,
          tipo: parsed.tipo,
          status: parsed.status,
          idempotency_key: parsed.idempotency_key,
          created_at: parsed.created_at,
        };

        setTxs((prev) => [tx, ...prev.filter((t) => t.id !== tx.id)]);
        return;
      }

      // ---- TX UPDATED ----
      if (base.event === 'tx_status_updated') {
        const parsed = safeJsonParse<TxStatusUpdatedEvent>(msg);
        if (!parsed) return;

        let found = false;

        setTxs((prev) => {
          found = prev.some((t) => t.id === parsed.id);
          if (!found) return prev;
          return prev.map((t) => (t.id === parsed.id ? { ...t, status: parsed.status } : t));
        });

        // Si no estaba en state, refrescamos lista desde backend
        if (!found) {
          void refreshTransactionsOnly();
        }

        return;
      }

      // ---- SUMMARY CREATED (pendiente inmediato incluso si viene de Playwright) ----
      if (base.event === 'summary_created') {
        const parsed = safeJsonParse<SummaryCreatedEvent>(msg);
        if (!parsed) return;

        void (async () => {
          try {
            const full = await api.getSummary(parsed.id);
            setSummaries((prev) => [full, ...prev.filter((s) => s.id !== full.id)]);
          } catch (e) {
            console.warn('Failed to fetch summary (created)', parsed.id, e);
            void refreshSummariesOnly();
          }
        })();

        return;
      }

      // ---- SUMMARY UPDATED ----
      if (base.event === 'summary_updated') {
        const parsed = safeJsonParse<SummaryUpdatedEvent>(msg);
        if (!parsed) return;

        setSummaries((prev) => {
          const exists = prev.some((s) => s.id === parsed.id);
          if (!exists) return prev;
          return prev.map((s) =>
            s.id === parsed.id
              ? {
                  ...s,
                  status: parsed.status,
                  result: s.result ?? (parsed.preview ?? null),
                }
              : s
          );
        });

        void (async () => {
          try {
            const full = await api.getSummary(parsed.id);
            setSummaries((prev) => [full, ...prev.filter((s) => s.id !== full.id)]);
          } catch (e) {
            console.warn('Failed to fetch summary (updated)', parsed.id, e);
          }
        })();

        return;
      }
    };

    ws.onerror = (ev) => console.warn('WS error', ev);
    ws.onclose = () => console.log('WS closed');

    return () => {
      ws.close();
      wsRef.current = null;
    };
  }, [wsUrl]);

  async function createTxAsync() {
    setError(null);
    const key = nowKey('async-tx');
    try {
      const created = await api.createAsync(txForm, key);
      setTxs((prev) => [created, ...prev.filter((t) => t.id !== created.id)]);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }

  async function createTxSync() {
    setError(null);
    const key = nowKey('sync-tx');
    try {
      const created = await api.createSync(txForm, key);
      setTxs((prev) => [created, ...prev.filter((t) => t.id !== created.id)]);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }

  async function createSummaryAsync() {
    setError(null);
    const key = nowKey('async-sum');
    try {
      const created = await api.createSummaryAsync(sumForm, key);
      setSummaries((prev) => [created, ...prev.filter((s) => s.id !== created.id)]);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }

  return (
    <div style={{ maxWidth: 1000, margin: '0 auto', padding: 24 }}>
      <h1>Prueba Full-Stack</h1>
      <p style={{ opacity: 0.8 }}>
        Backend: <code>/api</code> · WebSocket: <code>/ws/transactions/stream</code>
      </p>

      {error && (
        <div style={{ marginTop: 16, padding: 12, border: '1px solid #f00', borderRadius: 8 }}>
          <strong>Error:</strong> <span>{error}</span>
        </div>
      )}

      <div style={{ display: 'flex', gap: 12, marginTop: 16, flexWrap: 'wrap' }}>
        <button onClick={refreshAll} disabled={loading}>
          {loading ? 'Cargando...' : 'Refrescar todo'}
        </button>
      </div>

      <h2 style={{ marginTop: 24 }}>Transacciones</h2>

      <div style={{ display: 'flex', gap: 16, alignItems: 'flex-end', flexWrap: 'wrap' }}>
        <div>
          <label>User ID</label>
          <input value={txForm.user_id} onChange={(e) => setTxForm((p) => ({ ...p, user_id: e.target.value }))} />
        </div>

        <div>
          <label>Monto</label>
          <input
            type="number"
            step="0.01"
            value={txForm.monto}
            onChange={(e) => setTxForm((p) => ({ ...p, monto: Number(e.target.value) }))}
          />
        </div>

        <div>
          <label>Tipo</label>
          <input value={txForm.tipo} onChange={(e) => setTxForm((p) => ({ ...p, tipo: e.target.value }))} />
        </div>

        <button onClick={createTxAsync}>Crear (tx async + WS)</button>
        <button onClick={createTxSync}>Crear (tx sync)</button>
      </div>

      <div style={{ overflowX: 'auto', marginTop: 12 }}>
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr>
              <th style={{ textAlign: 'left', borderBottom: '1px solid #ddd', padding: 8 }}>ID</th>
              <th style={{ textAlign: 'left', borderBottom: '1px solid #ddd', padding: 8 }}>User</th>
              <th style={{ textAlign: 'right', borderBottom: '1px solid #ddd', padding: 8 }}>Monto</th>
              <th style={{ textAlign: 'left', borderBottom: '1px solid #ddd', padding: 8 }}>Tipo</th>
              <th style={{ textAlign: 'left', borderBottom: '1px solid #ddd', padding: 8 }}>Status</th>
              <th style={{ textAlign: 'left', borderBottom: '1px solid #ddd', padding: 8 }}>Idempotency</th>
              <th style={{ textAlign: 'left', borderBottom: '1px solid #ddd', padding: 8 }}>Created</th>
            </tr>
          </thead>
          <tbody>
            {txs.map((t) => (
              <tr key={t.id}>
                <td style={{ borderBottom: '1px solid #eee', padding: 8, fontFamily: 'monospace' }}>{t.id.slice(0, 8)}…</td>
                <td style={{ borderBottom: '1px solid #eee', padding: 8 }}>{t.user_id}</td>
                <td style={{ borderBottom: '1px solid #eee', padding: 8, textAlign: 'right' }}>{t.monto.toFixed(2)}</td>
                <td style={{ borderBottom: '1px solid #eee', padding: 8 }}>{t.tipo}</td>
                <td style={{ borderBottom: '1px solid #eee', padding: 8, fontFamily: 'monospace' }}>{t.status}</td>
                <td style={{ borderBottom: '1px solid #eee', padding: 8, fontFamily: 'monospace' }}>{t.idempotency_key}</td>
                <td style={{ borderBottom: '1px solid #eee', padding: 8 }}>{new Date(t.created_at).toLocaleString()}</td>
              </tr>
            ))}
            {txs.length === 0 && !loading && (
              <tr>
                <td colSpan={7} style={{ padding: 16, opacity: 0.7 }}>
                  No hay transacciones.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <h2 style={{ marginTop: 28 }}>Summaries</h2>

      <div style={{ display: 'flex', gap: 16, alignItems: 'flex-end', flexWrap: 'wrap' }}>
        <div>
          <label>Source</label>
          <input value={sumForm.source} onChange={(e) => setSumForm((p) => ({ ...p, source: e.target.value }))} />
        </div>

        <div style={{ flex: 1, minWidth: 320 }}>
          <label>Text</label>
          <textarea
            rows={3}
            style={{ width: '100%' }}
            value={sumForm.text}
            onChange={(e) => setSumForm((p) => ({ ...p, text: e.target.value }))}
          />
        </div>

        <button onClick={createSummaryAsync}>Crear summary (async + WS)</button>
      </div>

      <div style={{ overflowX: 'auto', marginTop: 12 }}>
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr>
              <th style={{ textAlign: 'left', borderBottom: '1px solid #ddd', padding: 8 }}>ID</th>
              <th style={{ textAlign: 'left', borderBottom: '1px solid #ddd', padding: 8 }}>Source</th>
              <th style={{ textAlign: 'left', borderBottom: '1px solid #ddd', padding: 8 }}>Status</th>
              <th style={{ textAlign: 'left', borderBottom: '1px solid #ddd', padding: 8 }}>Result/Preview</th>
              <th style={{ textAlign: 'left', borderBottom: '1px solid #ddd', padding: 8 }}>Created</th>
            </tr>
          </thead>
          <tbody>
            {summaries.map((s) => (
              <tr key={s.id}>
                <td style={{ borderBottom: '1px solid #eee', padding: 8, fontFamily: 'monospace' }}>{s.id.slice(0, 8)}…</td>
                <td style={{ borderBottom: '1px solid #eee', padding: 8 }}>{s.source}</td>
                <td style={{ borderBottom: '1px solid #eee', padding: 8, fontFamily: 'monospace' }}>{s.status}</td>
                <td style={{ borderBottom: '1px solid #eee', padding: 8 }}>{s.result ?? ''}</td>
                <td style={{ borderBottom: '1px solid #eee', padding: 8 }}>{new Date(s.created_at).toLocaleString()}</td>
              </tr>
            ))}
            {summaries.length === 0 && !loading && (
              <tr>
                <td colSpan={5} style={{ padding: 16, opacity: 0.7 }}>
                  No hay summaries.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
