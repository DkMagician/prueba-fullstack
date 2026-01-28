#!/usr/bin/env bash
set -euo pipefail

BACKEND="http://127.0.0.1:8000"

echo "== Demo Prueba Full-Stack =="
echo "UI: http://localhost:5173"
echo ""

echo "[0] Health check"
curl -s "$BACKEND/health"; echo
echo ""

echo "[1] TX async (pendiente -> procesado via worker + WS)"
TX_KEY="demo-tx-$(date +%s)"
curl -s -X POST "$BACKEND/transactions/async-process" \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: $TX_KEY" \
  -d '{"user_id":"u1","monto":42.42,"tipo":"pago"}'
echo
echo "Idempotency-Key: $TX_KEY"
echo ""

echo "[2] Summary async manual (pendiente -> procesado via worker + WS)"
SUM_KEY="demo-sum-$(date +%s)"
curl -s -X POST "$BACKEND/summaries/async" \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: $SUM_KEY" \
  -d '{"source":"manual","text":"Demo rápida: resumen asíncrono con Redis/RQ y updates en tiempo real por WebSocket."}'
echo
echo "Idempotency-Key: $SUM_KEY"
echo ""

echo "[3] RPA Playwright (Wikipedia -> Summary async)"
echo "Ejecuta en otra terminal (backend venv):"
echo "  cd ~/prueba-fullstack/backend"
echo "  source .venv/bin/activate"
echo "  python3 scripts/rpa_wikipedia.py \"https://es.wikipedia.org/wiki/FastAPI\" rpa-demo-1"
echo ""
echo "TIP: Si quieres ver eventos en crudo:"
echo "  websocat ws://127.0.0.1:8000/transactions/stream"
