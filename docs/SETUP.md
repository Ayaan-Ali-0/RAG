# TenBit RAG — Setup Guide

> **Philosophy:** The platform starts with **zero API keys**. Each tenant brings their own LLM key. OCR is local by default (PaddleOCR). No external dependencies required to get started.

---

## Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [Clone the Repository](#2-clone-the-repository)
3. [Environment Setup](#3-environment-setup)
   - [Option A: Docker (Recommended)](#option-a-docker-recommended)
   - [Option B: Local Development](#option-b-local-development)
4. [Generate Encryption Key](#4-generate-encryption-key-required)
5. [Start the Platform](#5-start-the-platform)
6. [Verify All Services Are Running](#6-verify-all-services-are-running)
7. [First-Time Configuration](#7-first-time-configuration)
8. [Create Your First Tenant](#8-create-your-first-tenant)
9. [OCR Engine Setup](#9-ocr-engine-setup)
10. [Testing the Full Pipeline](#10-testing-the-full-pipeline)
11. [Production Deployment](#11-production-deployment)
12. [Troubleshooting](#12-troubleshooting)

---

## 1. Prerequisites

### Required Tools

Check each tool is installed with the minimum version:

```bash
# Check Docker (required: 24+)
docker --version
# Expected output: Docker version 24.0.7, build ...

# Check Docker Compose (required: 2.20+)
docker compose version
# Expected output: Docker Compose version v2.20.3

# Check Git (required: 2.30+)
git --version
# Expected output: git version 2.30.0

# Check Python (required: 3.11+)
python --version
# Expected output: Python 3.11.0

# Check cURL (any version)
curl --version
# Expected output: curl 8.0.1 ...
```

### Install Missing Tools

<details>
<summary><b>Windows (PowerShell)</b></summary>

```powershell
# Install Docker Desktop (requires WSL2)
# Download from: https://docs.docker.com/desktop/setup/install/windows-install/

# Install Git
winget install --id Git.Git -e --source winget

# Install Python 3.11+
winget install --id Python.Python.3.11 -e --source winget

# Verify
docker --version && docker compose version && git --version && python --version
```
</details>

<details>
<summary><b>Ubuntu / Debian</b></summary>

```bash
# Install Docker
sudo apt-get update
sudo apt-get install -y ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Add current user to docker group
sudo usermod -aG docker $USER
# Log out and back in for this to take effect

# Verify
docker --version
docker compose version

# Install Python 3.11
sudo apt-get install -y python3.11 python3.11-venv python3-pip
python3.11 --version
```
</details>

<details>
<summary><b>macOS (Homebrew)</b></summary>

```bash
# Install Docker Desktop
brew install --cask docker

# Install Python
brew install python@3.11

# Install Git
brew install git

# Verify
docker --version && docker compose version && python3 --version
```
</details>

---

## 2. Clone the Repository

```bash
# Clone with HTTPS
git clone https://github.com/Ayaan-Ali-0/RAG.git tenbit-rag

# OR clone with SSH
git clone git@github.com:Ayaan-Ali-0/RAG.git tenbit-rag

# Enter the project directory
cd tenbit-rag

# Verify you're in the right place
ls
# Expected output: docker-compose.yml  docker/  docs/  ocr-service-main/  pyproject.toml  src/  ...
```

---

## 3. Environment Setup

Choose one of two paths:

### Option A: Docker (Recommended)

Docker runs all services in isolated containers. No local Python setup needed.

```bash
# 1. Copy the Docker environment template
cp .env.docker .env

# 2. Open .env in a text editor and configure the required values
#    At minimum, you need RAG_ENCRYPTION_KEY (see step 4)
#    You'll generate the actual key in the next step
```

### Option B: Local Development

For developers who want to run the Python code outside Docker (e.g., for debugging).

```bash
# 1. Copy the example environment
cp .env.example .env

# 2. Create a Python virtual environment
python -m venv venv

# 3. Activate the virtual environment
# ── Windows (PowerShell) ──
.\venv\Scripts\Activate.ps1

# ── Windows (cmd) ──
.\venv\Scripts\activate.bat

# ── Linux / macOS ──
source venv/bin/activate

# 4. Verify activation (your prompt should show (venv))
which python
# Expected: .../tenbit-rag/venv/bin/python (Linux/macOS)
# OR
where.exe python
# Expected: ...\tenbit-rag\venv\Scripts\python.exe (Windows)

# 5. Install the project in editable mode with all dependencies
pip install -e ".[dev]"

# 6. Install OCR dependencies (optional)
pip install -e ".[ocr]"

# If you get a "no module named cryptography" error:
pip install cryptography pyjwt httpx qdrant-client

# 7. Verify everything installed correctly
python -c "from cryptography.fernet import Fernet; print('cryptography OK'); import jwt; print('pyjwt OK'); import httpx; print('httpx OK')"
# Expected output:
# cryptography OK
# pyjwt OK
# httpx OK
```

---

## 4. Generate Encryption Key (Required)

The encryption key secures tenant API keys at rest using AES-256-GCM via Fernet.

```bash
# ── Run this command ──
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

**Expected output** (example — your key will be different):
```
dGhpcyBpcyBhbiBleGFtcGxlIGJhc2U2NCBlbmNvZGVkIGZvciB0ZXN0aW5nIHB1cnBvc2VzIG9ubHk=
```

**Now add it to your `.env` file:**

```bash
# Append the key to .env
echo "RAG_ENCRYPTION_KEY=dGhpcyBpcyBhbiBleGFtcGxlIGJhc2U2NCBlbmNvZGVkIGZvciB0ZXN0aW5nIHB1cnBvc2VzIG9ubHk=" >> .env
```

<details>
<summary><b>Verify the key is in .env</b></summary>

```bash
grep RAG_ENCRYPTION_KEY .env
# Expected output:
# RAG_ENCRYPTION_KEY=dGhpcyBpcyBhbiBleGFtcGxlIGJhc2U2NCBlbmNvZGVkIGZvciB0ZXN0aW5nIHB1cnBvc2VzIG9ubHk=
```
</details>

---

## 5. Start the Platform

### Option A: Docker (Recommended)

```bash
# ── STAGE 1: Pull images and build ──
docker compose build

# ── STAGE 2: Start all services in background ──
docker compose up -d

# ── STAGE 3: Wait for services to be ready (30-60 seconds) ──
# Check logs to see startup progress
docker compose logs --tail=50 -f
# Press Ctrl+C when you see services are up

# ── STAGE 4: Verify services are up ──
docker compose ps
```

**Expected output from `docker compose ps`:**
```
NAME                     IMAGE                           COMMAND                   SERVICE             STATUS              PORTS
tenbit-rag-api           tenbit-rag-rag_api               "uvicorn main:app..."      rag_api             running             0.0.0.0:8000->8000/tcp
tenbit-nginx             nginx:alpine                    "nginx -g daemon off;"     nginx               running             0.0.0.0:80->80/tcp
tenbit-ocr               tenbit-rag-ocr_service           "uvicorn main:app..."      ocr_service         running
tenbit-qdrant            qdrant/qdrant:latest             "./entrypoint.sh"          qdrant              running             0.0.0.0:6333->6333/tcp
tenbit-redis             redis:7-alpine                   "redis-server"             redis               running             6379/tcp
tenbit-scraper           tenbit-rag-scraper_service       "uvicorn main:app..."      scraper_service     running
```

### Option B: Local Development (without Docker)

You need to start each service manually. In separate terminal windows:

**Terminal 1 — Start Qdrant (vector database):**
```bash
# Run Qdrant in a Docker container (or install natively)
docker run -d --name tenbit-qdrant -p 6333:6333 qdrant/qdrant:latest
```

**Terminal 2 — Start Redis (cache):**
```bash
docker run -d --name tenbit-redis -p 6379:6379 redis:7-alpine
```

**Terminal 3 — Start the main RAG API:**
```bash
cd tenbit-rag
source venv/bin/activate   # Linux/macOS
# OR .\venv\Scripts\Activate.ps1  # Windows
cd src
uvicorn rbs_rag.web.server:app --reload --host 0.0.0.0 --port 8000
```

**Terminal 4 — Start the OCR service (optional):**
```bash
cd tenbit-rag
source venv/bin/activate
cd ocr-service-main
uvicorn main:app --reload --host 0.0.0.0 --port 8001
```

---

## 6. Verify All Services Are Running

```bash
# ── 6a. Check the main API health endpoint ──
curl http://localhost/api/v1/health
```

**Expected response:**
```json
{"status":"ok","version":"1.0.0","services":{"qdrant":"connected","redis":"connected","ocr_service":"connected"}}
```

```bash
# ── 6b. Check individual service endpoints (Docker only) ──

# Check Qdrant directly
curl -s http://localhost:6333/ | python -m json.tool
# Expected: {"title":"qdrant","version":"1.12.0",...}

# Check Redis is running
docker exec tenbit-redis redis-cli ping
# Expected output: PONG

# Check OCR service
curl http://localhost:8001/health
# Expected response: {"status":"ok"}

# Check nginx proxy
curl -s -o /dev/null -w "%{http_code}" http://localhost/
# Expected output: 200
```

```bash
# ── 6c. Docker container resource usage ──
docker stats --no-stream
# Shows CPU/memory for all running containers
```

---

## 7. First-Time Configuration

### 7a. Set Required Environment Variables

Edit `.env` and configure these:

```bash
# Open .env in your editor
notepad .env               # Windows
nano .env                  # Linux/macOS

# Ensure the following are set (minimum viable config):
RAG_ENCRYPTION_KEY=<your-generated-key>
RAG_ADMIN_JWT_SECRET=your-super-secret-jwt-key-at-least-32-chars
RAG_ADMIN_PASSWORD=change-this-password
```

### 7b. Restart Services After Config Changes

**Docker:**
```bash
docker compose down && docker compose up -d
```

**Local dev:** Stop the uvicorn process (Ctrl+C) and restart it.

### 7c. Environment Variables Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `RAG_LLM_API_KEY` | No | — | Global LLM fallback — leave empty for per-tenant keys |
| `RAG_LLM_PROVIDER` | No | `gemini` | `gemini`, `openai_compatible`, or `anthropic` |
| `RAG_LLM_MODEL` | No | `gemini-2.5-flash-lite` | Model name |
| `QDRANT_HOST` | No | `qdrant` | Qdrant hostname (`localhost` for local dev) |
| `QDRANT_PORT` | No | `6333` | Qdrant port |
| `RAG_ROOT_DIR` | No | `/data/.rbs_rag` | Container data path |
| `RAG_ENCRYPTION_KEY` | **Yes** | — | Fernet key (44-char base64) for encrypting API keys |
| `RAG_ADMIN_JWT_SECRET` | Yes* | — | JWT secret for admin auth (≥ 32 chars). Leave empty to disable auth. |
| `RAG_ADMIN_PASSWORD` | Yes* | `admin` | Admin dashboard password |
| `RAG_TERMINAL_ENABLED` | No | `false` | Set `true` to enable the terminal endpoint |
| `MISTRAL_API_KEY` | No | — | Mistral cloud OCR (falls back to PaddleOCR) |
| `NEMOTRON_API_KEY` | No | — | NVIDIA Nemotron OCR (requires separate NIM container) |
| `DEEPCRAWL_API_KEY` | No | — | Cloudflare bypass for scraper |
| `RAG_CORS_ORIGINS` | No | `*` | Allowed CORS origins |
| `UVICORN_WORKERS` | No | `1` | Number of uvicorn workers (increase on multi-core) |

> **Multi-tenant note:** Leave `RAG_LLM_API_KEY` empty. Each tenant supplies their own LLM API key when created via API or dashboard.

---

## 8. Create Your First Tenant

The platform starts empty — no tenants, no API keys. Create one with curl:

### 8a. Create a Tenant with Gemini

```bash
curl -X POST http://localhost/api/v1/tenants \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_id": "acme-corp",
    "name": "Acme Corporation",
    "llm_provider": "gemini",
    "llm_model": "gemini-2.5-flash-lite",
    "llm_api_key": "your-gemini-api-key-here",
    "embedding_provider": "hash"
  }'
```

**Expected response:**
```json
{"tenant_id":"acme-corp","name":"Acme Corporation","status":"created"}
```

### 8b. Create a Tenant with OpenAI-compatible (e.g., OpenAI, Groq, Together)

```bash
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
```

### 8c. Create a Tenant with Anthropic

```bash
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

### 8d. List All Tenants

```bash
curl http://localhost/api/v1/tenants
```

**Expected response:**
```json
[{"tenant_id":"acme-corp","name":"Acme Corporation","llm_provider":"gemini","llm_model":"gemini-2.5-flash-lite"},{"tenant_id":"megacorp","name":"MegaCorp Inc","llm_provider":"openai_compatible","llm_model":"gpt-4o-mini"},{"tenant_id":"startup-xyz","name":"Startup XYZ","llm_provider":"anthropic","llm_model":"claude-3-5-sonnet-20241022"}]
```

### 8e. Delete a Tenant

```bash
curl -X DELETE http://localhost/api/v1/tenants/acme-corp
```

**Expected response:**
```json
{"status":"deleted","tenant_id":"acme-corp"}
```

---

## 9. OCR Engine Setup

### 9a. Default: PaddleOCR (Local, No API Key)

PaddleOCR runs inside the `ocr_service` container. It downloads model files (~15MB) on first use.

```bash
# Verify PaddleOCR is available
curl http://localhost:8001/health
# Expected: {"status":"ok","engine":"paddle"}
```

### 9b. Mistral OCR (Cloud)

Set the `MISTRAL_API_KEY` in `.env`:

```bash
echo "MISTRAL_API_KEY=your-mistral-api-key" >> .env
docker compose restart ocr_service
```

### 9c. NVIDIA Nemotron OCR (Local NIM Container)

Set the `NEMOTRON_API_KEY` in `.env`:

```bash
echo "NEMOTRON_API_KEY=your-nemotron-api-key" >> .env
docker compose restart ocr_service
```

Additionally, you need to run the Nemotron NIM container:

```bash
docker run -d --gpus all \
  --name tenbit-nemotron \
  -p 8000:8000 \
  -e NEMOTRON_API_KEY=your-nemotron-api-key \
  nvcr.io/nvidia/nim/nvlm-d:72b
```

The OCR service will automatically discover the Nemotron engine and use it when `NEMOTRON_API_KEY` is set.

### 9d. Check Available OCR Engines

```bash
curl http://localhost:8001/engines
```

**Expected response with PaddleOCR only:**
```json
{"engines":["paddle"],"primary_engine":"paddle"}
```

**Expected response with Mistral key:**
```json
{"engines":["paddle","mistral"],"primary_engine":"paddle"}
```

**Expected response with Nemotron key:**
```json
{"engines":["paddle","nemotron"],"primary_engine":"paddle"}
```

---

## 10. Testing the Full Pipeline

### 10a. Upload a Document

```bash
# Create a test document
echo "This is a test document for the RAG platform. It contains information that will be processed by the ingestion pipeline." > test-document.txt

# Upload to tenant's knowledge base
curl -X POST http://localhost/api/v1/tenants/acme-corp/documents \
  -F "file=@test-document.txt" \
  -F "kb_id=default"
```

**Expected response:**
```json
{"status":"uploaded","document_id":"doc-xxx","filename":"test-document.txt","size":123}
```

### 10b. Ingest the Document (Chunk → Embed → Store)

```bash
curl -X POST http://localhost/api/v1/tenants/acme-corp/ingest
```

**Expected response:**
```json
{"status":"completed","documents_processed":1,"chunks_created":3}
```

### 10c. Chat with the Document

```bash
curl -X POST http://localhost/api/v1/tenants/acme-corp/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "What does this document say?", "session_id": "test-1"}'
```

**Expected response:**
```json
{"answer":"The document is a test document for the RAG platform. It contains information that will be processed by the ingestion pipeline.","sources":[{"document_id":"doc-xxx","relevance_score":0.95}]}
```

### 10d. Search Documents

```bash
curl "http://localhost/api/v1/tenants/acme-corp/search?q=test+document&k=5"
```

**Expected response:**
```json
[{"chunk_id":"...","text":"...","score":0.95}]
```

### 10e. Access the Admin Dashboard

Open http://localhost in a browser.

If you set `RAG_ADMIN_JWT_SECRET`, log in first:

```bash
curl -X POST http://localhost/api/v1/admin/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"<your-RAG_ADMIN_PASSWORD>"}'
```

**Expected response:**
```json
{"token":"eyJhbGciOiJIUzI1NiIs...","expires_in":86400}
```

### 10f. Run the Python Verification Script

For local development setups:

```bash
# From the project root
python -c "
import sys, os
sys.path.insert(0, 'src')
os.environ['RAG_ENCRYPTION_KEY'] = 'a' * 44

from rbs_rag.text import cosine_similarity
from rbs_rag.security import encrypt_api_key, decrypt_api_key, generate_jwt, verify_jwt
from rbs_rag.embeddings import create_embedding_provider
from rbs_rag.store import SQLiteRagStore
from rbs_rag.config import AppConfig, ChunkingConfig
from rbs_rag.chunking import create_chunker
from rbs_rag.validation import validate_retrieval
from rbs_rag.reranking import create_reranker
from rbs_rag.vector_store import QdrantVectorStore
from rbs_rag.web.admin_db import AdminStore
from pathlib import Path
import tempfile

# Core tests
assert abs(cosine_similarity([1,0,0],[1,0,0]) - 1.0) < 1e-10
enc = encrypt_api_key('secret'); assert decrypt_api_key(enc) == 'secret'
ep = create_embedding_provider('hash', 8, 'test'); emb = ep.embed(['hello']); assert len(emb[0]) == 8
store = SQLiteRagStore(Path(tempfile.mkdtemp())/'test.db')
config = AppConfig(); assert config.storage.provider == 'sqlite'
chunker = create_chunker(ChunkingConfig()); assert chunker is not None
assert validate_retrieval([]).sufficient == False
reranker = create_reranker('local'); assert reranker is not None
qs = QdrantVectorStore(config.vector_store.qdrant); assert qs.is_initialized == False
adm = AdminStore(Path(tempfile.mkdtemp())/'admin.db'); assert adm is not None

print('All 10 verification tests passed!')
"
```

**Expected output:**
```
All 10 verification tests passed!
```

---

## 11. Production Deployment

### 11a. Generate Strong Secrets

```bash
# Generate a Fernet encryption key (44-char base64)
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# Generate a random 32-character password
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Generate a JWT secret (at least 32 characters)
python -c "import secrets; print(secrets.token_hex(32))"
```

### 11b. Set Up HTTPS

```bash
# Create SSL directory
mkdir -p nginx/ssl

# Place your certificate files there
#   nginx/ssl/cert.pem  — fullchain certificate
#   nginx/ssl/key.pem   — private key

# For Let's Encrypt (after domain is set up):
# sudo apt-get install certbot
# sudo certbot certonly --standalone -d yourdomain.com
# sudo cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem nginx/ssl/cert.pem
# sudo cp /etc/letsencrypt/live/yourdomain.com/privkey.pem nginx/ssl/key.pem
```

### 11c. Configure CORS

```bash
echo "RAG_CORS_ORIGINS=https://app.yourdomain.com" >> .env
```

### 11d. Scale Workers

```bash
echo "UVICORN_WORKERS=8" >> .env
# Half of available CPU cores is a good starting point
```

### 11e. Backup Data

```bash
# Backup all volumes
docker run --rm -v tenbit-rag_rag_data:/data -v $(pwd):/backup alpine \
  tar czf /backup/rag-backup-$(date +%Y%m%d).tar.gz -C /data .

# Restore from backup
docker run --rm -v tenbit-rag_rag_data:/data -v $(pwd):/backup alpine \
  tar xzf /backup/rag-backup-20241201.tar.gz -C /data
```

### 11f. Monitoring

```bash
# View live logs
docker compose logs -f --tail=100

# View logs for a single service
docker compose logs -f rag_api --tail=50

# Restart a single service
docker compose restart rag_api

# Check disk usage
docker system df

# Platform stop / start (preserves volumes)
docker compose down
docker compose up -d

# Full clean (destroys all data)
docker compose down -v
```

---

## 12. Troubleshooting

### 12a. Common Errors

| Error | Likely Cause | Fix |
|-------|-------------|-----|
| `Connection refused` when curling localhost | Services not started | Run `docker compose up -d` and wait 30s |
| `ModuleNotFoundError: No module named 'cryptography'` | Missing Python dependency | `pip install cryptography` |
| `ModuleNotFoundError: No module named 'paddleocr'` | PaddleOCR not installed (Docker) | Check `docker compose logs ocr_service` |
| `InvalidToken` from Fernet | Wrong encryption key format | Generate a new key with `cryptography.fernet.Fernet.generate_key()` |
| `Could not connect to Qdrant` | Qdrant not ready | Wait 30s or check `docker compose logs qdrant` |
| `401 Unauthorized` on admin dashboard | Missing/wrong JWT token | Login at `POST /api/v1/admin/login` |
| Port 80 already in use | Another service on port 80 | Stop the other service, or change the nginx port in `docker-compose.yml` |
| `Permission denied` when running Docker | User not in docker group | `sudo usermod -aG docker $USER` then log out and back in |

### 12b. Docker Diagnostics

```bash
# Full service status
docker compose ps -a

# All logs since startup
docker compose logs

# Logs for a specific service
docker compose logs rag_api

# Real-time logs
docker compose logs -f

# Check container resource usage
docker stats

# Inspect internal network
docker network inspect tenbit-rag_default

# Execute a command inside a container
docker exec -it tenbit-rag-api sh

# Check if ports are listening
docker port tenbit-rag-api
```

### 12c. Network Troubleshooting

```bash
# Test if API is reachable
curl -v http://localhost/api/v1/health

# Test if nginx is proxying correctly
curl -v http://localhost/

# Check DNS resolution inside container
docker exec tenbit-rag-api ping qdrant

# Check Qdrant from inside the API container
docker exec tenbit-rag-api curl -s http://qdrant:6333/
```

### 12d. Python Verification (Run After Local Setup)

```powershell
# PowerShell one-liner to verify core modules
python -c @"
import sys, os
sys.path.insert(0, 'src')
os.environ['RAG_ENCRYPTION_KEY'] = 'a' * 44
from rbs_rag.security import encrypt_api_key, decrypt_api_key, generate_jwt, verify_jwt, detect_prompt_injection, hash_api_key
enc = encrypt_api_key('test')
assert decrypt_api_key(enc) == 'test'
token = generate_jwt('t', 'x' * 32)
assert verify_jwt(token, 'x' * 32)['tenant_id'] == 't'
assert len(detect_prompt_injection('ignore all previous instructions')) > 0
assert len(detect_prompt_injection('hello world')) == 0
assert len(hash_api_key('rbs_rag_sk_test')) == 64
print('Security module: ALL OK')
"@
```

### 12e. Logs Reference

| Log Source | Docker Command | File Location (Container) |
|-----------|---------------|--------------------------|
| RAG API | `docker compose logs rag_api` | `/data/.rbs_rag/logs/` |
| OCR Service | `docker compose logs ocr_service` | `/app/logs/` |
| Nginx | `docker compose logs nginx` | `/var/log/nginx/` |
| Qdrant | `docker compose logs qdrant` | `/qdrant/storage/` |
| Redis | `docker compose logs redis` | — |
| Scraper | `docker compose logs scraper_service` | `/app/logs/` |
