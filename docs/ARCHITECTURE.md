# TenBit RAG Platform — Architecture

## Overview

TenBit RAG is a hybrid retrieval-augmented generation platform designed for multi-tenant enterprise deployments. It combines dense vector search (Qdrant + cosine similarity) with sparse keyword retrieval (BM25) fused via Reciprocal Rank Fusion (RRF), followed by reranking and LLM-based answer generation.

---

## 1. Hybrid Retrieval (`retrieval.py`, `text.py`, `reranking.py`)

Retrieval follows a **4-phase** pipeline inside `HybridRetriever.search_with_profile()`:

| Phase | Component | Details |
|-------|-----------|---------|
| 1 | **Dense (Qdrant)** | Query is embedded via the configured `EmbeddingProvider`, then searched in Qdrant using cosine distance. Returns up to `top_k * 2` candidates. |
| 2 | **Fallback (SQLite)** | If Qdrant returns zero results, chunks are fetched from the SQLite store and dense similarity is computed locally via `cosine_similarity()` (`text.py:15`). |
| 3 | **Sparse (BM25)** | BM25 scores are computed using `bm25_scores()` (`text.py:29`) with k1=1.5, b=0.75 across all candidate chunks. |
| 4 | **Fusion (RRF)** | Dense and sparse scores are converted to reciprocal ranks (`_rank_scores()` at `retrieval.py:123`). Fused via: `score = 0.55 * dense_rank + 0.45 * sparse_rank`. Configurable via `dense_weight` / `sparse_weight`. |
| 5 | **Reranking** | Top-k candidates are reranked by a `Reranker` (`reranking.py`). Default is `LocalReranker` (query-chunk token overlap + phrase bonus). Optionally `BGECrossEncoderReranker` when `sentence_transformers` is installed. |

The `LLMSettings` config controls retrieval parameters: `top_k = 20`, `rerank_top_k = 8`, `final_context_k = 5`.

---

## 2. Data Flow: Document Ingestion → Answer

```
User Upload
    │
    ▼
Document Loader ──┬── Text files → direct read
                  ├── PDF → PyMuPDF text extraction → OCR fallback
                  ├── Images → OCR pipeline
                  └── Other → per-type readers
    │
    ▼
Chunker (configurable max_tokens=320, overlap=48, optional semantic)
    │
    ▼
Embedding Provider ──┬── HashEmbedding (deterministic, no API)
                     ├── FastEmbed/BGE (local ML)
                     ├── OpenAI-Compatible (API)
                     └── Gemini (API)
    │
    ├──▶ SQLite Store ─── chunks table (tenant_id, kb_id, text, embedding JSON)
    └──▶ Qdrant Vector Store ── collection "rag_chunks" (COSINE distance, 384d default)
              │
              ▼
User Query ──▶ 1. Embed query
               2. Hybrid Search (Qdrant + BM25 + RRF)
               3. Rerank
               4. Build RAG messages (system prompt + context + session memory)
               5. LLM generate (sync or streaming)
               6. Store session turn in SQLite
               7. Return Answer(text, citations, validation, profile)
```

---

## 3. Multi-Tenant Isolation

Each tenant is isolated at both storage layers:

| Layer | Isolation Strategy |
|-------|-------------------|
| **SQLite** | Every row in `documents`, `chunks`, `session_turns`, and `user_memory` is tagged with `tenant_id`. All queries filter by `tenant_id`. |
| **Qdrant** | Each tenant can have a separate collection (collection name convention). Document metadata includes `tenant_id` for filtered search. |

The `RagEngine` operates with a single `tenant_id` from `AppConfig`. In a multi-tenant deployment, a separate `RagEngine` instance (or a tenant-scoped API wrapper) is created per tenant.

---

## 4. Security (`security.py`)

| Mechanism | Description |
|------------|-------------|
| **Fernet Encryption** | API keys are encrypted with `cryptography.fernet.Fernet` using a master key from `RAG_ENCRYPTION_KEY` env var (`encrypt_api_key` / `decrypt_api_key`). Falls back to a dev-only SHA-256 derived key. |
| **Tenant API Key Hashing** | Keys are generated as `rbs_rag_sk_{tenant_id}_{random}` and stored as SHA-256 hashes (`generate_api_key`, `validate_api_key`). |
| **JWT Admin Auth** | `generate_jwt()` creates HS256 JWTs with `tenant_id`, `iat`, `exp`, and `jti`. `verify_jwt()` validates them. Controlled by `SecurityConfig.admin_auth_enabled`. |
| **Prompt Injection Detection** | `detect_prompt_injection()` scans for patterns like "ignore previous instructions", "act as if", role-play prompts, and embedded role-switching via regex patterns defined in `INJECTION_PATTERNS` (`security.py:66`). |
| **Rate Limiting** | Configurable per-minute rate limit with burst support via `RateLimitConfig`. |

---

## 5. Async Architecture

External API calls use **httpx with connection pooling**:

| Client | Type | Pool / Limits |
|--------|------|---------------|
| `_get_client()` (`llm.py:267`) | `httpx.Client` | Shared singleton, timeout 120s / connect 30s |
| `_get_async_client()` (`llm.py:303`) | `httpx.AsyncClient` | Per-call, limits: max_keepalive=5, max_connections=10 |
| `QdrantVectorStore` | `qdrant_client` | gRPC preferred, with HTTP fallback |
| Embedding APIs | `httpx.Client` | Per-call, timeout 45s |

Streaming LLM endpoints use `async for chunk in client.stream("POST", ...)` with SSE line parsing. Fallback model chains retry on 429/503/UNAVAILABLE errors.

---

## 6. OCR Pipeline (`ocr/engines/orchestrator.py`)

The OCR orchestrator chains three engines in priority order with automatic fallback:

| Priority | Engine | Availability | Type |
|----------|--------|-------------|------|
| 1st | **NemotronOCR** | `NemotronOCREngine` — requires API key + NIM endpoint (default `http://localhost:8000`) | Cloud / Self-hosted NVIDIA NIM |
| 2nd | **Mistral OCR** | `MistralOCREngine` — requires `MISTRAL_API_KEY` (endpoint `https://api.mistral.ai/v1/ocr`) | Cloud API |
| 3rd | **PaddleOCR** | `PaddleOCREngine` — local, GPU optional, no API key | Local (paddleocr) |

The engine priority is configurable via `primary_engine` parameter ("nemotron", "mistral", or "paddle"). The orchestrator selects the first available engine that returns non-empty text; if it fails, it falls through to the next.

OCR is applied when:
- `use_ocr=True` is passed to `ingest_file()` / `ingest_path()`
- The file is an image (`.png`, `.jpg`, `.jpeg`, `.tiff`, `.bmp`, `.webp`)
- A PDF is scanned (embedded text extraction yields too few characters)

---

## 7. LLM Routing (`llm.py`)

Multi-provider support with automatic provider detection:

| Provider | Client | Detection |
|----------|--------|-----------|
| **Gemini** | `GeminiClient` | API key starts with `AIza`, or model starts with `gemini`, or URL contains `generativelanguage.googleapis.com` |
| **OpenAI** | `OpenAICompatibleClient` | Default catch-all; also used for NVIDIA, OpenRouter, Groq, Together, Fireworks, custom endpoints |
| **Anthropic** | `AnthropicClient` | URL contains `anthropic.com`, model starts with `claude`, or key starts with `sk-ant` |
| **Ollama** | Via OpenAI-compatible client | Works with any OpenAI-compatible base URL (e.g., `http://localhost:11434/v1`) |

Key routing features:
- **Configurable per-tenant**: `LLMSettings` supports `provider`, `api_key`, `model`, `base_url`, `fallback_models`
- **Fallback chain**: If the primary model returns 429/503/UNAVAILABLE, fallback models are tried in order via `_unique_models()`
- **Streaming**: All clients support async SSE streaming via `generate_stream()`
- **Connection pooling**: Shared httpx client singleton reuses connections across requests
- **Per-tenant settings** are resolved from `AppConfig.llm`, which can be overridden per tenant via the config file or environment variables (`${RAG_LLM_API_KEY}`)

---

## 8. Storage Layer

### SQLite (`store.py`)
- **Schema**: `documents`, `chunks`, `session_turns`, `user_memory`, `health` tables
- **Tenant-aware**: Every table includes `tenant_id` for isolation
- **Migration support**: Graceful column addition via `ALTER TABLE ... ADD COLUMN` in `_migrate_schema()`
- **Chunk storage**: Embeddings stored as JSON text in `embedding_json` column

### Qdrant (`vector_store.py`)
- **Collection**: "rag_chunks" with configurable vector size (default 384) and COSINE distance
- **Payload**: Stores `chunk_id`, `document_id`, `text`, `ordinal`, `metadata_json`
- **Filtering**: Supports `knowledge_base_id` and arbitrary metadata field filters via `_build_filter()`
- **Batch operations**: Upserts in batches of 64, supports batch search for multi-query scenarios
- **Graceful degradation**: All Qdrant operations catch exceptions; if Qdrant is unavailable, the system falls back to SQLite-only retrieval

---

## 9. Key Configuration (`config.py`)

| Section | Key Parameters |
|---------|---------------|
| `RetrievalConfig` | top_k=20, dense_weight=0.55, sparse_weight=0.45, reranker="local" |
| `ChunkingConfig` | max_tokens=320, overlap_tokens=48, semantic_chunking=false |
| `EmbeddingConfig` | provider="hash", dimensions=384, model="BAAI/bge-small-en-v1.5" |
| `LLMSettings` | provider="gemini", model="gemini-2.5-flash-lite", fallback_models |
| `QdrantConfig` | host="localhost", port=6333, prefer_grpc=false |
| `SecurityConfig` | encrypt_keys=false, admin_auth_enabled=false, prompt_injection_detection=false |

Config values support `${ENV_VAR}` substitution, loading from `.env` / `.env.local` files.

---

## 10. Request Lifecycle (End-to-End)

```
Client Request (REST / CLI)
    │
    ▼
RagEngine.ask() / ask_stream()
    │
    ├── 1. HybridRetriever.search_with_profile()
    │       ├── a. Embed query via EmbeddingProvider
    │       ├── b. Qdrant vector search (top_k * 2)
    │       ├── c. If Qdrant empty → SQLite fallback + local cosine sim
    │       ├── d. BM25 sparse scoring across candidates
    │       ├── e. RRF fusion (dense_rank + sparse_rank)
    │       ├── f. Rerank top candidates
    │       └── g. Return ranked SearchResults + timing profile
    │
    ├── 2. Retrieve session memory & user memory
    │
    ├── 3. Build RAG messages (system prompt + context + memory + query)
    │
    ├── 4. LLM generate (sync or async stream)
    │
    ├── 5. Store conversation turn in SQLite
    │
    └── 6. Return Answer with citations, validation, and profiling telemetry
```