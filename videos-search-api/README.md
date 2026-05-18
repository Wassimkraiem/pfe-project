# BVIRAL Project

## Overview

BVIRAL is a video management platform with a RESTful API for creating, retrieving, searching, and deleting video documents. It provides a Python SDK for easy integration, so your team can use its features without deep knowledge of the API internals.

---

## Running the Project Locally

### Prerequisites

- Docker & Docker Compose installed
- Python 3.8+ (for SDK usage)

### Start the App

1. Clone the repository:
   ```bash
   git clone <your-repo-url>
   cd BVIRAL
   ```
2. Copy and configure your `.env` file as needed.
3. Start the services:
   ```bash
   docker compose -f docker-compose.local.yml up
   ```
4. The API will be available at `http://http://localhost:5000` by default.

---

## API Usage

### Endpoints

- `POST   /api/videos/` — Create or update a video
- `DELETE /api/videos/` — Delete a video (by JSON body)
- `POST   /api/videos/query` — Search videos (by JSON body)
- `GET    /api/videos/query` — Get all videos

### Example: Create a Video (with curl)

```bash
curl -X POST http://http://localhost:5000/api/videos/ \
     -H 'Content-Type: application/json' \
     -d '{
           "video_id": "test123",
           "service_identifier": "rms",
           "video_data": {"title": "Test Video", "views": 42}
         }'
```

## Python SDK Usage

### Installation

Copy `bviral_sdk.py` into your project or package it as a module.

### Example Usage

```python
from bviral_sdk import BviralSDK

sdk = BviralSDK("http://http://localhost:5000",API_KEY="key1")

# Create a video
data = {
    "video_id": "test123",
    "service_identifier": "rms",
    "video_data": {"title": "Test Video", "views": 42}
}
print(sdk.create_video(data))

# Get a video by ID
print(sdk.get_video("test123"))

# Search for videos
print(sdk.search_videos({"title": "Test Video"}))

# Delete a video
print(sdk.delete_video("test123"))
```

## Search Caching (Redis)

The `/api/videos/advanced-search` endpoint caches responses in Redis to make
repeat queries near-instant. Caching is transparent: the cache key is a SHA-1
hash of the normalized request (query, filters, sort, pagination, strategy),
so the same request always returns the same cached result until its TTL
expires.

Configuration (env vars):

- `REDIS_URL` (default: `redis://localhost:6379/0`) — connection URL.
- `SEARCH_CACHE_TTL` (default: `300`) — cache entry lifetime in seconds.
- `SEARCH_CACHE_ENABLED` (default: `true`) — set to `false` to disable.

Every response from `/api/videos/advanced-search` includes a `cache` field:

```json
{
  "items": [...],
  "total": 42,
  "execution": { "total_ms": 8, "cache_lookup_ms": 1, ... },
  "cache": { "hit": true, "key": "adv_search:v1:<sha1>" }
}
```

On a hit the full retrieval/fusion/rerank pipeline is skipped. Failures to
reach Redis are swallowed and the request transparently falls through to
OpenSearch. The `debug` block, when requested, is never cached.

A `videos-redis` service is provided in both the root `docker-compose.yml`
and `videos-search-api/docker-compose.local.yml`.

## Video Embeddings

Semantic search uses 1536-dimension OpenAI embeddings stored in the
`embedding` knn vector field. New writes go through the `videos_write` alias
and reads go through `videos_read`.

Required environment variables:

- `OPENAI_API_KEY` — OpenAI API key used for embeddings.
- `EMBEDDING_PROVIDER=openai`
- `EMBEDDING_MODEL=text-embedding-3-small`
- `EMBEDDING_DIMENSION=1536`
- `VIDEOS_READ_ALIAS=videos_read`
- `VIDEOS_WRITE_ALIAS=videos_write`

OpenAI reranking is a last resort by default. The normal path uses lexical +
vector retrieval, RRF fusion, and a local heuristic reranker. Set
`ADVANCED_SEARCH_OPENAI_RERANK_MODE=always` only for evaluation or when latency
is acceptable.

The lexical branch uses OpenSearch's default BM25 scoring through `multi_match`.
Hybrid ranking then applies QMD-style RRF bonuses: rank #1 in either BM25 or
vector results gets `+0.05`, and ranks #2-3 get `+0.02`. The default rerank
window is `ADVANCED_SEARCH_RERANK_TOP_N=30`.

Before importing new rows, run the importer with `--ensure-index` so the
vectorized index and aliases are bootstrapped. Existing `videos` documents can
be migrated with `scripts/backfill_video_embeddings.py`.

---

## Search Accuracy + Speed Benchmark

Use the benchmark test to compare `/api/videos/vsearch` and `/api/videos/advanced-search` on the same judged queries.

1. Prepare judged dataset:
   - Copy `search_eval_dataset.example.json` to `search_eval_dataset.json`.
   - Replace `REPLACE_WITH_REAL_VIDEO_ID_*` with real IDs and graded relevance.
2. Run benchmark:
   ```bash
   make test-search-eval
   ```

Environment variables:
- `SEARCH_API_URL` (default: `http://127.0.0.1:5000`)
- `SEARCH_API_KEY` (default: `key1`)
- `SEARCH_EVAL_DATASET` (default: `./search_eval_dataset.json`)
- `SEARCH_EVAL_K` (default: `20`)
- Optional pass/fail thresholds:
  - `SEARCH_EVAL_MIN_ADV_NDCG`
  - `SEARCH_EVAL_MIN_NDCG_LIFT`
  - `SEARCH_EVAL_MAX_ADV_P95_MS`

---

## Contributing

Feel free to open issues or submit pull requests for improvements!

---

## License

MIT (or your chosen license)
