# RUN GUIDE — RAG Platform

## From fresh Windows to working system in 5 commands

---

### 1. Install Docker Desktop

Download from [docker.com](https://docs.docker.com/desktop/setup/install/windows-install/) and install.  
After install, launch Docker Desktop and wait for the engine to start (tray icon stops spinning).

> **WSL2 alternative (free, no license needed):**  
> Run as Administrator: `wsl --install -d Ubuntu` → restart → open PowerShell → `wsl -d Ubuntu -e bash -c "curl -fsSL https://get.docker.com | sh"` → `wsl --shutdown`. Then use `wsl -d Ubuntu -e docker` instead of `docker` below.

---

### 2. Extract the project

Unzip the project folder to a permanent location, e.g. `C:\RAG\`.

Open **PowerShell** in that folder:

```powershell
cd C:\RAG
```

---

### 3. Configure (one file)

```powershell
Copy-Item .env.example .env
```

No API keys are needed to start the platform. The `.env.example` already has safe defaults.

LLM API keys are configured **per client (tenant)** when you create them via the admin dashboard or API. This lets you start the system with zero API keys and add them later for each individual client.

---

### 4. Start everything

```powershell
docker compose up -d
```

Wait 2–3 min while Docker builds the images and downloads dependencies.

---

### 5. Verify

```powershell
curl http://localhost/api/v1/health
```

Expected: `{"status":"ok","db":"connected","qdrant":"connected","llm":"unknown",...}`

---

### 6. Create a client (with their LLM API key)

```powershell
curl -X POST http://localhost/api/v1/tenants -H "Content-Type: application/json" -d "{\"tenant_id\":\"demo\",\"name\":\"Demo Client\",\"llm_api_key\":\"their-gemini-or-openai-key\"}"
```

Each client brings their own LLM API key. Save the returned **API key** (`rbs_rag_sk_...`) — you'll give it to your client for API access.

OCR (PaddleOCR) and Scraper (Playwright) services run fully locally. No API keys needed for those services unless you want Mistral OCR or DeepCrawl Cloudflare bypass.

---

### Access URLs

| Page | URL |
|------|-----|
| Admin dashboard | http://localhost |
| Chat widget | http://localhost/widget |
| OCR API | http://localhost/ocr/docs |
| Scraper API | http://localhost/crawl/test |
| Qdrant UI | http://localhost:6333/dashboard |

---

### If something goes wrong

```powershell
docker compose ps          # check all 6 services are "Up"
docker logs tenbit-rag-api --tail 20   # check RAG API logs
docker logs tenbit-ocr --tail 20       # check OCR logs
docker logs tenbit-scraper --tail 20   # check Scraper logs
```
