# All-in-One Docker Run

This repository now supports running all projects together from the root with a single Docker Compose file.

## Services Included

- `videosearch-portal` (Next.js): http://localhost:3002
- `authentic-rights-portal` (Next.js): http://localhost:3001
- `ar-api` (FastAPI): http://localhost:8001
- `agentic-helper-api` (FastAPI): http://localhost:8003
- `videos-search-api` (Flask): http://localhost:5000
- `opensearch-dashboards`: http://localhost:5601
- `opensearch-node1`: http://localhost:9200
- `agentic-helper-db` (Postgres): localhost:5432
- `ar-celery-worker`
- `ar-celery-beat`

## Prerequisites

- Docker + Docker Compose plugin installed
- Environment files present:
  - `AR-api/.env`
  - `agentic-helper/.env`

If needed:

```bash
cp AR-api/.env.example AR-api/.env
cp agentic-helper/.env.example agentic-helper/.env
```

## Start Everything

```bash
docker compose up -d --build
```

## Check Status

```bash
docker compose ps
```

## View Logs

```bash
docker compose logs -f
```

## Stop Everything

```bash
docker compose down
```

## Stop and Remove Volumes (reset DB/index data)

```bash
docker compose down -v
```

## Notes

- Browser-facing `NEXT_PUBLIC_*` URLs are mapped to `localhost` ports.
- Server-to-server URLs use Docker service names inside the network.
- `videos-search-api` is configured with `API_KEYS=key1` by default in the root compose.
- `ar-api` may require valid third-party credentials (Stripe/Clerk/etc.) for some endpoints.
