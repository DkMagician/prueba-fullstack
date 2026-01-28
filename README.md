# Prueba Full-Stack Python — FastAPI + React + Redis/RQ + WebSocket + Playwright (RPA)

## 1) Introducción

Aplicación full-stack con:

- **Transactions**: creación idempotente + procesamiento asíncrono (Redis/RQ) + updates en tiempo real (WebSocket).
- **Summaries**: generación asíncrona (simulada) + updates en tiempo real (WebSocket).
- **RPA**: Playwright extrae texto desde Wikipedia y dispara un summary asíncrono.

---

## 2) Arquitectura (alto nivel)

**Frontend (React + Vite + TypeScript)**

- HTTP via proxy: `http://localhost:5173/api/*` → `http://127.0.0.1:8000/*`
- WS via proxy: `ws://localhost:5173/ws/*` → `ws://127.0.0.1:8000/*`
- La UI muestra `pendiente` inmediatamente y actualiza a `procesado` al recibir eventos por WebSocket.

**Backend (FastAPI + SQLModel)**

- DB: SQLite (`backend/app.db`)
- Expone REST endpoints y un WebSocket (`/transactions/stream`)
- Reenvía eventos de Redis Pub/Sub a todos los clientes conectados por WebSocket.

**Async (Redis + RQ)**

- Worker procesa jobs y actualiza estado en SQLite
- Publica eventos en Redis Pub/Sub (canal `tx-events`) para que el backend los retransmita por WS.

**RPA (Playwright)**

- Script `backend/scripts/rpa_wikipedia.py`: extrae texto de una URL y lo manda al endpoint async de summaries.

---

## 3) Decisiones técnicas (por qué elegi estas tecnologias)

- **SQLite**: simple, cero infraestructura extra, suficiente para una prueba.
- **Redis + RQ**: cola ligera, fácil de correr local (menos fricción que Celery/Kafka).
- **Redis Pub/Sub + WebSocket**: realtime sin polling, fan-out simple.
- **Vite proxy**: evita CORS y simplifica rutas (`/api`, `/ws`).

---

## 4) Instrucciones para correr el proyecto

### 4.1 Requisitos

- Ubuntu 24.04+
- Python 3.12+
- Node 18+ (o 20+)
- Redis (`redis-server`) activo
- (Opcional para WS en crudo) `websocat`

#### Instalar Redis (si no se tiene)

```bash
sudo apt update
sudo apt install -y redis-server
sudo systemctl enable --now redis-server
redis-cli ping
```

**Esperado:** `PONG`

#### Verificar Node/NPM

```bash
node -v
npm -v
```

---

### 4.2 Clonar el repositorio

```bash
git clone https://github.com/DkMagician/prueba-fullstack.git
cd prueba-fullstack
```

---

### 4.3 Levantar el proyecto (En 4 terminales)

#### Terminal A — Redis

```bash
sudo systemctl restart redis-server
redis-cli ping
```

**Esperado:** `PONG`

---

#### Terminal B — Backend (FastAPI)

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate

pip install -U pip
pip install fastapi "uvicorn[standard]" sqlmodel redis rq httpx

uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

**Validación:**

```bash
curl -s http://127.0.0.1:8000/health && echo
```

**Respuesta Esperada:**

```json
{ "ok": true }
```

**Nota:** si `backend/.venv` ya existe,se omite `python3 -m venv .venv` y solo se activa el entorno.

---

#### Terminal C — Worker (RQ)

```bash
cd backend
source .venv/bin/activate
rq worker --url redis://localhost:6379 default
```

**Respuesta Esperada:** ver `Listening on default...`

---

#### Terminal D — Frontend (React/Vite)

```bash
cd frontend
npm install
npm run dev
```

**Abrir UI:**

- http://localhost:5173

**Validación proxy:**

```bash
curl -s http://localhost:5173/api/health && echo
```

**Respuesta Esperada:**

```json
{ "ok": true }
```

---

### 4.4 (Opcional para verificación) Ver eventos del WebSocket “en crudo”

```bash
websocat ws://127.0.0.1:8000/transactions/stream
```

---

### 4.5 Demo rápida (2–3 min)

Desde la raíz del repo:

```bash
./demo.sh
```

**Qué esperar en UI:**

- Transaction: `pendiente` → `procesado` (realtime)
- Summary: `pendiente` → `procesado` (realtime)

---

### 4.6 RPA (Playwright) — Wikipedia → Summary async

#### Instalar Playwright (si no se tiene)

```bash
cd backend
source .venv/bin/activate
pip install playwright
python3 -m playwright install chromium
```

#### Ejecutar RPA

```bash
cd backend
source .venv/bin/activate
python3 scripts/rpa_wikipedia.py "https://es.wikipedia.org/wiki/FastAPI" rpa-demo-1
```

**Qué se esperar ver en la UI:**

- aparece un summary `source=web` en `pendiente`
- luego cambia a `procesado` por WebSocket

---

## 5) Endpoints principales

### Health

- `GET /health`

### Transactions

- `GET /transactions`
- `POST /transactions/create` (sync, idempotente con `Idempotency-Key`)
- `POST /transactions/async-process` (async con RQ + WS)

### Summaries

- `GET /summaries`
- `GET /summaries/{id}`
- `POST /summaries/async` (async con RQ + WS)

### WebSocket

- `WS /transactions/stream`
