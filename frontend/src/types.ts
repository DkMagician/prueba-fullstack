export type TransactionStatus = 'pendiente' | 'procesado' | 'fallido';

export interface Transaction {
  id: string;
  user_id: string;
  monto: number;
  tipo: string;
  status: TransactionStatus;
  idempotency_key: string;
  created_at: string; // ISO string
}

export interface TransactionCreate {
  user_id: string;
  monto: number;
  tipo: string;
}

export interface TxStatusUpdatedEvent {
  event: 'tx_status_updated';
  id: string;
  status: TransactionStatus;
  user_id?: string;
}

export interface Summary {
  id: string;
  source: string;
  status: TransactionStatus; // misma idea (pendiente/procesado/fallido)
  result: string | null;
  error: string | null;
  idempotency_key: string;
  created_at: string;
}

export interface SummaryCreate {
  source: string;
  text: string;
}

export interface SummaryUpdatedEvent {
  event: 'summary_updated';
  id: string;
  status: TransactionStatus;
  source?: string;
  preview?: string;
}

export interface SummaryCreatedEvent {
  event: 'summary_created';
  id: string;
  status: TransactionStatus;
  source?: string;
  idempotency_key?: string;
  created_at?: string;
}

export interface TxCreatedEvent {
  event: 'tx_created';
  id: string;
  user_id: string;
  monto: number;
  tipo: string;
  status: TransactionStatus;
  idempotency_key: string;
  created_at: string;
}
