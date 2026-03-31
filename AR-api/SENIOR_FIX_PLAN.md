# Senior Fix Plan — Async & Infrastructure Issues

These items were separated from `FIX_PLAN.md` because they require deeper knowledge of
the async Python runtime, connection pool tuning, and FastAPI's request lifecycle.

---

## Step S1 — Fix event loop blocking (root cause of 15s latency on all endpoints)
**Files:** `app/user/services.py`, `app/onboarding_session/services.py`

**Context:** The `clerk_backend_api` SDK's synchronous methods (e.g. `clerk_client.users.create()`)
block the event loop thread when called directly inside `async def` handlers, freezing ALL other
requests — including `/health` — for the duration of the Clerk API round-trip.
This is the confirmed root cause of the 15-second latency across every endpoint.

**Important:** The Clerk SDK already ships native async methods suffixed with `_async`
(e.g. `create_async`, `delete_async`). `app/auth/services.py` already uses these correctly
(`clerk_client.sessions.create_async(...)`, `clerk_client.sessions.create_token_async(...)`).
**Do NOT use `asyncio.to_thread` — use the native async methods instead.**

- [ ] In `app/user/services.py`, replace the `clerk_client.users.create(...)` call (around line 58):
  ```python
  # Before
  clerk_user = clerk_client.users.create(
      email_address=[user_in.email],
      first_name=user_in.first_name,
      last_name=user_in.last_name,
      password=user_in.password,
  )

  # After
  clerk_user = await clerk_client.users.create_async(
      email_address=[user_in.email],
      first_name=user_in.first_name,
      last_name=user_in.last_name,
      password=user_in.password,
  )
  ```

- [ ] In `app/onboarding_session/services.py`, replace the rollback Clerk call (around line 907):
  ```python
  # Before
  clerk_client.users.delete(user_id=clerk_user_id)

  # After
  await clerk_client.users.delete_async(user_id=clerk_user_id)
  ```

- [ ] Search the project for any remaining synchronous `clerk_client.*` calls (without `_async` suffix) inside `async def` methods:
  ```bash
  grep -rn "clerk_client\." app/ --include="*.py"
  ```
  Every call that is NOT already `*_async(...)` and sits inside an `async def` must be updated.

- [ ] Deploy to staging and run a load test:
  ```bash
  wrk -t4 -c20 -d15s https://ar-api.bv.media/health
  ```
  P99 latency should drop from ~15s to under 500ms.

- [ ] Verify onboarding completion still works end-to-end after the change.

---

## Step S2 — Parallelize SMS API calls in `_compute_custom_quote_state`
**File:** `app/onboarding_session/services.py` (lines 1074–1301)

**Context:** `_compute_custom_quote_state` calls each platform's follower-count API
sequentially inside a `for channel_url` loop. With 6 platforms × 30s timeout each,
a user submitting 3 channels can trigger up to 90 seconds of sequential I/O before
the response is returned. These calls are independent and should run concurrently.

**Recommended approach — parallelize within each URL (lower refactor risk):**

The inter-iteration caches (`instagram_cache`, `tiktok_cache`, etc.) make
full across-URL parallelism tricky. A safe intermediate approach is to run all 6
platform lookups for a single URL concurrently, then move to the next URL. This
bounds latency to one SMS API round-trip per URL instead of six.

- [ ] Read and fully understand the existing loop (lines 1122–1301) before making
  any changes. Map out which variables are shared across iterations.

- [ ] For each channel URL, build a list of coroutines for the platforms that match,
  run them with `asyncio.gather(*tasks, return_exceptions=True)`, then populate the
  caches and trigger list from the results.

  Skeleton:
  ```python
  for channel_url in normalized_channels:
      tasks: list[tuple[str, str, Coroutine]] = []

      if handle := self._extract_instagram_handle_from_url(channel_url):
          supported_detected = True
          if handle not in instagram_cache:
              tasks.append(("instagram", handle, self._get_instagram_follower_count(handle)))

      if handle := self._extract_tiktok_handle_from_url(channel_url):
          supported_detected = True
          if handle not in tiktok_cache:
              tasks.append(("tiktok", handle, self._get_tiktok_follower_count(handle)))

      # ... repeat for youtube, facebook, twitter, snapchat ...

      results = await asyncio.gather(*[t[2] for t in tasks], return_exceptions=True)

      for (platform, handle, _), result in zip(tasks, results):
          if isinstance(result, SMSAPIError):
              # populate cache with (None, True) — api_error=True
          elif isinstance(result, Exception):
              # unexpected error, log and treat as api_error
          else:
              # populate cache with (result, False)

      # trigger evaluation logic unchanged from current code
  ```

- [ ] Preserve all existing caching behavior — handles already in the cache must not
  trigger a new API call.

- [ ] Measure wall-clock time before and after with 3 multi-platform channels.
  Time should drop from ~(6 × API latency) to ~(1 × API latency) per URL.

- [ ] Regression test: verify all trigger flags (`HIGH_FOLLOWERS`, `UNSUPPORTED_PLATFORM`,
  `SMS_API_ERROR`, `UNKNOWN_FOLLOWER_COUNT`) still fire correctly after the refactor.

---

## Step S3 — Make `/health` async
**File:** `app/app.py` (line 362)

**Context:** The `/health` handler is defined as a synchronous `def`. FastAPI runs
sync handlers in a thread pool via `run_in_executor`. When the thread pool is saturated
by other blocking calls (e.g., Clerk SDK before Step S1 is fixed), `/health` queues
behind them. Making it `async` removes it from the thread pool entirely.

> **Prerequisite:** Step S1 should land first. Once the blocking Clerk calls are
> fixed, this becomes a minor optimization rather than a critical fix.

- [ ] Change line 362:
  ```python
  # Before
  @app.get("/health")
  def health() -> dict[str, str | int]:
      return {"status": "ok", "version": 3}

  # After
  @app.get("/health")
  async def health() -> dict[str, str | int]:
      return {"status": "ok", "version": 3}
  ```

- [ ] Verify: `curl -w "\nTime: %{time_total}s\n" https://ar-api.bv.media/health` responds in < 50ms.

---

## Step S4 — Configure DB connection pool explicitly
**Files:** `app/core/config.py`, `app/db/database.py`

**Context:** `create_async_engine` currently uses SQLAlchemy defaults: `pool_size=5`,
`max_overflow=10`. Under any real concurrent load, the 16th simultaneous DB request
queues and waits. `pool_pre_ping=True` also adds a `SELECT 1` round-trip on every
connection checkout.

**Before changing anything:**
- [ ] Check your Postgres `max_connections`: `SHOW max_connections;` on the DB.
- [ ] Calculate the ceiling: `pool_size × (max_overflow + 1) × uvicorn_worker_count < max_connections`.
  With 4 workers and `pool_size=10, max_overflow=20`: `10 × 21 × 4 = 840` connections — likely too many.
  Start conservative: `pool_size=5, max_overflow=10` (same as default) but make them explicit and tunable.

- [ ] In `app/core/config.py`, add:
  ```python
  DB_POOL_SIZE: int = 5
  DB_MAX_OVERFLOW: int = 10
  DB_POOL_TIMEOUT: int = 30
  DB_POOL_RECYCLE: int = 1800
  ```

- [ ] In `app/db/database.py`, update `create_async_engine`:
  ```python
  async_engine: AsyncEngine = create_async_engine(
      settings.DATABASE_URL,
      pool_pre_ping=True,
      pool_size=settings.DB_POOL_SIZE,
      max_overflow=settings.DB_MAX_OVERFLOW,
      pool_timeout=settings.DB_POOL_TIMEOUT,
      pool_recycle=settings.DB_POOL_RECYCLE,
  )
  ```

- [ ] Monitor connection usage in production for 24 hours after deploying. Tune
  `DB_POOL_SIZE` upward only if you observe pool timeout errors in logs.

---

## Step S5 — Fix synchronous JWKS validation blocking the event loop on every authenticated request
**File:** `app/auth/dependencies.py` (lines 13–14)

**Confirmed findings (source inspected):**
- `ClerkHTTPBearer.__init__` creates `PyJWKClient(uri=..., cache_jwk_set=True, lifespan=300)` — **no network call at init** ✅
- `_decode_token` calls `self.jwks_client.get_signing_key_from_jwt(token)` synchronously inside the `async def __call__` method — **this blocks the event loop on every authenticated request** ❌
- The JWKS response is cached for 300 seconds, so the actual network fetch only happens once per 5 minutes per worker. Cache hits still run synchronously but are fast (in-memory dict lookup).

**Impact:** Every authenticated endpoint blocks the event loop during `_decode_token`. Under
concurrent load, this serializes all authenticated requests. The 15s latency on authenticated
endpoints will persist even after S1 is fixed until this is addressed.

**Fix:** Wrap `_decode_token` in `asyncio.to_thread` inside `ClerkHTTPBearer.__call__`. Since
`fastapi_clerk_auth` is a third-party package, subclass it rather than patching the library:

```python
# app/auth/dependencies.py
import asyncio
from fastapi_clerk_auth import ClerkHTTPBearer, ClerkConfig, HTTPAuthorizationCredentials
from fastapi import Request
from typing import Optional

class AsyncClerkHTTPBearer(ClerkHTTPBearer):
    """Subclass that moves synchronous JWKS validation off the event loop."""

    async def __call__(self, request: Request) -> Optional[HTTPAuthorizationCredentials]:
        # Extract credentials using parent's logic but decode token in a thread
        authorization = request.headers.get("Authorization")
        from fastapi.security.utils import get_authorization_scheme_param
        from fastapi import HTTPException
        from starlette.status import HTTP_403_FORBIDDEN

        scheme, credentials = get_authorization_scheme_param(authorization)
        if not (authorization and scheme and credentials):
            if self.auto_error:
                raise HTTPException(status_code=HTTP_403_FORBIDDEN, detail="Forbidden")
            return None
        if scheme.lower() != "bearer":
            if self.auto_error:
                raise HTTPException(status_code=HTTP_403_FORBIDDEN, detail="Forbidden")
            return None

        decoded_token = await asyncio.to_thread(self._decode_token, token=credentials)

        if not decoded_token and self.auto_error:
            raise HTTPException(status_code=HTTP_403_FORBIDDEN, detail="Forbidden")
        response = HTTPAuthorizationCredentials(
            scheme=scheme, credentials=credentials, decoded=decoded_token
        )
        if self.add_state:
            request.state.clerk_auth = response
        return response
```

- [ ] Replace `clerk_auth_guard = ClerkHTTPBearer(config=clerk_config)` with
  `clerk_auth_guard = AsyncClerkHTTPBearer(config=clerk_config)` — no changes needed to
  any `Depends(clerk_auth_guard)` callers.

- [ ] Verify: authenticate a request and confirm `_decode_token` no longer runs on the event
  loop thread. A simple test: hit two authenticated endpoints simultaneously and confirm
  neither blocks the other.

> **Longer-term:** Open an issue or PR on `fastapi-clerk-auth` to make `_decode_token`
> async-native using `asyncio.to_thread` internally. The current library version (0.0.9) does
> not do this.

---

---

## Step S6 — Wrap all `task.delay()` calls in `asyncio.to_thread()`
**Files:** `app/onboarding_session/router.py` (lines 130, 158, 168, 206, 731), `app/onboarding_session/services.py` (line 886)

**Context:** Celery's `.delay()` uses a synchronous Redis connection (via `kombu` + `redis-py`)
to publish the task message. When called directly inside an `async def` handler, this
synchronous socket write runs on the event loop thread and blocks it. Under Redis load
or latency, every endpoint that enqueues a task will stall all other requests.

There are 6 occurrences across the onboarding module:

| File | Line | Task |
|---|---|---|
| `router.py` | 130 | `send_setup_account_email_task.delay()` |
| `router.py` | 158 | `send_custom_quote_created_email_task.delay()` |
| `router.py` | 168 | `send_custom_quote_team_notification_email_task.delay()` |
| `router.py` | 206 | `send_custom_quote_price_submitted_email_task.delay()` |
| `router.py` | 731 | `send_welcome_email_task.delay()` |
| `services.py` | 886 | `create_basic_canto_user_task.delay()` |

- [ ] Search for any other `.delay()` calls elsewhere in the FastAPI app (not in Celery tasks):
  ```bash
  grep -rn "\.delay(" app/ --include="*.py" | grep -v "celery\|periodics\|tasks\.py"
  ```

- [ ] Wrap each occurrence. Pattern for router.py:
  ```python
  # Before
  send_welcome_email_task.delay(
      recipient_email=session.email,
      first_name=payload.first_name,
      recipient_name=recipient_name,
  )

  # After
  await asyncio.to_thread(
      send_welcome_email_task.delay,
      recipient_email=session.email,
      first_name=payload.first_name,
      recipient_name=recipient_name,
  )
  ```

- [ ] Add `import asyncio` to `router.py` (it is not currently imported there).

- [ ] Verify: confirm all endpoints that enqueue tasks still work end-to-end after wrapping.

> **Long-term alternative:** Celery has experimental async support via `celery.contrib.pytest`
> and third-party libraries like `aio-celery`. If the team migrates to async Celery,
> all `.delay()` wrappers can be removed. For now, `asyncio.to_thread()` is the correct fix.

---

## Step S7 — Parallelize `_verify_channel()` calls in `complete_onboarding_session_by_uuid`
**File:** `app/onboarding_session/services.py` (lines 806–832)

**Context:** Channel verification in the onboarding completion flow runs sequentially:

```python
for channel_url in channels:
    (username, follower_count, verification_status) = await self._verify_channel(...)
    channel = await channel_service.create(channel_data)
```

Each `_verify_channel` call has a 30-second timeout. With 5 channels, worst case is
150 seconds before the loop completes. Critically, the **database session stays open
the entire time** — one connection held hostage from the pool for up to 150 seconds.
These calls are independent and can safely run concurrently.

- [ ] Separate the verification step from the DB insert step:

  ```python
  # Step 1: verify all channels concurrently
  verification_tasks = [
      self._verify_channel(str(url), self._detect_platform_from_url(str(url)))
      for url in channels
  ]
  verification_results = await asyncio.gather(*verification_tasks, return_exceptions=True)

  # Step 2: insert channels into DB (fast, sequential is fine here)
  for channel_url, result in zip(channels, verification_results):
      channel_url_str = str(channel_url)
      platform = self._detect_platform_from_url(channel_url_str)

      if isinstance(result, Exception):
          logger.warning("Channel verification failed for %s: %s", channel_url_str, result)
          username, follower_count, verification_status = None, None, VerificationStatus.FAILED
      else:
          username, follower_count, verification_status = result

      channel_data = ChannelCreateSchema(
          user_id=user.id,
          url=channel_url_str,
          platform=platform,
          username=username,
          follower_count=follower_count,
          verification_status=verification_status,
      )
      channel = await channel_service.create(channel_data)
      created_channels.append(channel.id)
  ```

- [ ] Apply the same pattern to the channel verification inside `mark_payment_received`
  (around line 452) where channels from webhook metadata are also verified sequentially.

- [ ] Verify: complete onboarding with 5 channels and confirm total time drops from
  ~(5 × API latency) to ~(1 × API latency).

---

## Execution Order

```
WEEK 1
  ├── S1  Async Clerk SDK calls        ← do this first, fixes the 15s latency
  └── S6  Wrap task.delay() calls      ← low risk, high impact, do alongside S1

  → Deploy to staging immediately after S1 + S6
  → Load test: verify P99 drops to < 500ms across all endpoints
  → Deploy to production

WEEK 2
  ├── S2  Parallelize SMS API calls in _compute_custom_quote_state  ← largest change
  ├── S7  Parallelize _verify_channel in complete_onboarding         ← same pattern as S2, do together
  ├── S3  Make /health async                                         ← quick win, low risk
  └── S4  DB pool config                                             ← check Postgres max_connections first

WEEK 3
  └── S5  Investigate ClerkHTTPBearer init
```
