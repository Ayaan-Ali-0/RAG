# TenBit RAG — One-Command New Machine Setup

> **Philosophy:** The platform starts with **zero API keys**. Each tenant brings their own LLM key. OCR is local by default (PaddleOCR). No external dependencies required to get started.

---

## 1. Prerequisites

| Tool | Minimum | Check |
|------|---------|-------|
| **Docker** | 24+ | `docker --version` |
| **Docker Compose** | 2.20+ | `docker compose version` |
| **Git** | 2.30+ | `git --version` |
| **Python** | 3.11+ | `python --version` |
| **cURL** | any | `curl --version` |

---

## 2. Clone & Quick Start

```bash
git clone <repo-url> tenbit-rag
cd tenbit-rag

# ── ONE COMMAND ──────────────────────────────────────────────────
docker compose up -d
# ─────────────────────────────────────────────────────────────────

# Platform is now running at http://localhost
```

That's it. The platform boots with:

| Service | Container | Purpose |
|---------|-----------|---------|
| `rag_api` | `tenbit-rag-api` | RAG core + admin dashboard |
| `qdrant` | `tenbit-qdrant` | Vector store |
| `redis` | `tenbit-redis` | Cache + rate limiting |
| `ocr_service` | `tenbit-ocr` | OCR (PaddleOCR local) |
| `scraper_service` | `tenbit-scraper` | Web scraping |
| `nginx` | `tenbit-nginx` | Reverse proxy (port 80) |

---

## 3. First-Time Configuration

Copy the template and edit:

```bash
cp .env.docker .env
```

### Environment Variables Explained

| Variable | Required | Description |
|----------|----------|-------------|
| `RAG_LLM_API_KEY` | No | Global LLM fallback — **leave empty** for per-tenant keys |
| `RAG_LLM_PROVIDER` | No | `gemini`, `openai_compatible`, or `anthropic` |
| `RAG_LLM_MODEL` | No | Model name (e.g. `gemini-2.5-flash-lite`) |
| `QDRANT_HOST` | No | Qdrant host (`qdrant` in Docker) |
| `QDRANT_PORT` | No | Qdrant port (`6333`) |
| `RAG_ROOT_DIR` | No | Container data path (`/data/.rbs_rag`) |
| `RAG_ENCRYPTION_KEY` | **Yes** | Fernet key for encrypting stored API keys |
| `RAG_ADMIN_JWT_SECRET` | **Yes** | JWT secret for admin auth (set to enable auth) |
| `RAG_ADMIN_PASSWORD` | **Yes** | Admin login password (default: `admin`) |
| `RAG_TERMINAL_ENABLED` | No | Enable terminal endpoint (`true`) |
| `MISTRAL_API_KEY` | No | Mistral cloud OCR (PaddleOCR used when empty) |
| `NEMOTRON_API_KEY` | No | NVIDIA Nemotron OCR NIM container |
| `DEEPCRAWL_API_KEY` | No | Cloudflare bypass for scraper |

> **Multi-tenant note:** Leave `RAG_LLM_API_KEY` empty. Each tenant supplies their own LLM API key when created via API or dashboard.

---

## 4. Generate Encryption Key (Required)

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Copy the output into `.env`:

```env
RAG_ENCRYPTION_KEY=generated-base64-key-here==
```

---

## 5. Security

| Variable | Purpose | How to Set |
|----------|---------|------------|
| `RAG_ENCRYPTION_KEY` | Encrypts tenant API keys at rest (AES-256-GCM via Fernet) | Generate with `python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"` |
| `RAG_ADMIN_JWT_SECRET` | Enables admin authentication on dashboard | Set any string ≥ 32 chars. Login: `POST /api/v1/admin/login` with `admin` / `RAG_ADMIN_PASSWORD` |
| `RAG_ADMIN_PASSWORD` | Admin password | Change from default `admin` in production |

**Set both `RAG_ADMIN_JWT_SECRET` and `RAG_ADMIN_PASSWORD` to lock down the admin dashboard.** Leave `RAG_ADMIN_JWT_SECRET` empty to keep auth disabled.

---

## 6. OCR Setup

| Engine | Type | API Key Required | Notes |
|--------|------|-----------------|-------|
| **PaddleOCR** | Local (ONNX) | No | Runs inside `ocr_service` container, ~15MB first download |
| **Mistral OCR** | Cloud | `MISTRAL_API_KEY` | Falls back to PaddleOCR if not set |
| **NVIDIA Nemotron OCR v2** | Local NIM container | `NEMOTRON_API_KEY` | Requires running NVIDIA NIM container separately at `localhost:8000` |

PaddleOCR is the default. Set `MISTRAL_API_KEY` or `NEMOTRON_API_KEY` only if you want those engines.

---

## 7. Creating the First Tenant

The platform starts empty — no tenants, no API keys. Create one with curl:

```bash
# ── Create tenant with Gemini ────────────────────────────────────
curl -X POST http://localhost/api/v1/tenants \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_id": "acme-corp",
    "name": "Acme Corporation",
    "llm_provider": "gemini",
    "llm_model": "gemini-2.5-flash-lite",
    "llm_api_key": "your-gemini-api-key",
    "embedding_provider": "hash"
  }'

# ── Create tenant with OpenAI ────────────────────────────────────
curl -X POST http://localhost/api/v1/tenants \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_id": "megacorp",
    "name": "MegaCorp Inc",
    "llm_provider": "openai_compatible",
    "llm_model": "gpt-4o-mini",
    "llm_api_key": "sk-...",
    "llm_base_url": "https://api.openai.com/v1",
    "embedding_provider": "hash"
  }'

# ── Create tenant with Anthropic ────────────────────────────────
curl -X POST http://localhost/api/v1/tenants \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_id": "startup-xyz",
    "name": "Startup XYZ",
    "llm_provider": "anthropic",
    "llm_model": "claude-3-5-sonnet-20241022",
    "llm_api_key": "sk-ant-...",
    "llm_base_url": "https://api.anthropic.com/v1",
    "embedding_provider": "hash"
  }'
```

Each tenant's API key is encrypted at rest using `RAG_ENCRYPTION_KEY`.

---

## 8. Verifying the Platform

```bash
# ── Health check ─────────────────────────────────────────────────
curl http://localhost/api/v1/health

# ── List tenants ────────────────────────────────────────────────
curl http://localhost/api/v1/tenants

# ── Upload a document ───────────────────────────────────────────
curl -X POST http://localhost/api/v1/tenants/acme-corp/documents \
  -F "file=@document.pdf" \
  -F "kb_id=default"

# ── Ingest ──────────────────────────────────────────────────────
curl -X POST http://localhost/api/v1/tenants/acme-corp/ingest

# ── Chat ────────────────────────────────────────────────────────
curl -X POST http://localhost/api/v1/tenants/acme-corp/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "What does this document say?", "session_id": "test-1"}'
```

**Dashboard:** Open http://localhost in a browser. If `RAG_ADMIN_JWT_SECRET` is set, login at `POST /api/v1/admin/login` with username `admin` and password from `RAG_ADMIN_PASSWORD`.

---

## 9. Production Deployment Tips

```bash
# ── Use a strong encryption key ──────────────────────────────────
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# ── Set a strong admin password and JWT secret ──────────────────
# RAG_ADMIN_PASSWORD=<generated-password>
# RAG_ADMIN_JWT_SECRET=<32+ char random string>

# ── Enable HTTPS ────────────────────────────────────────────────
# Place SSL certs in ./nginx/ssl/
#   cert.pem  — fullchain
#   key.pem   — private key

# ── Set CORS origins ────────────────────────────────────────────
# RAG_CORS_ORIGINS=https://app.yourdomain.com

# ── Increase uvicorn workers on multi-core hosts ────────────────
# UVICORN_WORKERS=8

# ── Back up volumes ─────────────────────────────────────────────
docker run --rm -v tenbit-rag_rag_data:/data -v $(pwd):/backup alpine \
  tar czf /backup/rag-backup-$(date +%Y%m%d).tar.gz -C /data .

# ── View logs ────────────────────────────────────────────────────
docker compose logs -f --tail=100

# ── Restart single service ──────────────────────────────────────
docker compose restart rag_api

# ── Platform stop / start ──────────────────────────────────────
docker compose down
docker compose up -d
```