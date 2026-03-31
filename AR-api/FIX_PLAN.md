# Fix Plan — Onboarding Session & Performance Issues

> **Before touching any code**, run this read-only query on production to assess existing plaintext password exposure:
> ```sql
> SELECT COUNT(*)
> FROM onboarding_sessions
> WHERE session_details -> 'account' -> 'password' IS NOT NULL;
> ```
> If the result is > 0, the data remediation script in Step 1.1 must run immediately after deploying that step.

---

## Phase 1 — Critical (Ship First)

Each step = one commit. Do them in order.

---

### Step 1.1 — Exclude password from session_details JSON
**File:** `app/onboarding_session/services.py`

- [ ] Find line 347:
  ```python
  account_dict = account_data.model_dump(mode="json")
  ```
  Replace with:
  ```python
  account_dict = account_data.model_dump(mode="json", exclude={"password", "confirm_password"})
  ```

- [ ] Deploy, then run this data remediation SQL on production:
  ```sql
  UPDATE onboarding_sessions
  SET session_details = jsonb_set(
      jsonb_set(session_details, '{account,password}', 'null'),
      '{account,confirm_password}', 'null'
  )
  WHERE session_details -> 'account' IS NOT NULL;
  ```

- [ ] Verify: call the account update endpoint, then query the DB and confirm `session_details->'account'` has no `password` or `confirm_password` keys.

---

### Step 1.2 — Guard against double-completion (idempotency)
**File:** `app/onboarding_session/services.py`

- [ ] In `complete_onboarding_session_by_uuid`, after the `if not session: raise OnboardingSessionNotFound(...)` block (around line 741), add:
  ```python
  if session.current_step == OnboardingStep.COMPLETED:
      raise AppError(
          message="Onboarding already completed",
          error_code="onboarding_already_completed",
          status_code=HTTPStatus.CONFLICT,
      )
  ```

- [ ] Verify: call `POST /{session_uuid}/account` twice with the same UUID. The second call must return 409. Check Clerk dashboard — only one user should exist for that email.

---

### Step 1.3 — Fix naive datetimes in Stripe webhook handler
**File:** `app/onboarding_session/services.py`

`timezone` is already imported — no import change needed.

- [ ] Lines 397 and 410 — replace both occurrences of:
  ```python
  datetime.fromtimestamp(created_at) if isinstance(created_at, int) else datetime.utcnow()
  ```
  with:
  ```python
  datetime.fromtimestamp(created_at, tz=timezone.utc) if isinstance(created_at, int) else datetime.now(timezone.utc)
  ```

- [ ] Line 421 — replace:
  ```python
  payment_completed_at = datetime.utcnow()
  ```
  with:
  ```python
  payment_completed_at = datetime.now(timezone.utc)
  ```

- [ ] Line 854 — replace:
  ```python
  f"order_{datetime.utcnow().timestamp()}"
  ```
  with:
  ```python
  f"order_{datetime.now(timezone.utc).timestamp()}"
  ```

- [ ] Verify: send a mock Stripe webhook, check the stored `payment_completed_at` in the DB has a `+00:00` offset.

---

### Step 1.4 — Fix platform detection using substring matching
**File:** `app/onboarding_session/services.py`

- [ ] Find `_detect_platform_from_url` (around line 1714). Replace the entire method body:
  ```python
  @staticmethod
  def _detect_platform_from_url(url: str) -> Platform | None:
      """Detect platform from channel URL."""
      parsed = urlparse(url)
      domain = parsed.netloc.lower()
      if domain.startswith("www."):
          domain = domain[4:]

      if domain == "instagram.com":
          return Platform.INSTAGRAM
      elif domain in {"tiktok.com", "vm.tiktok.com"}:
          return Platform.TIKTOK
      elif domain in {"youtube.com", "youtu.be"}:
          return Platform.YOUTUBE
      elif domain == "facebook.com":
          return Platform.FACEBOOK
      return None
  ```

- [ ] Verify: unit test that `notinstagram.com`, `instagram.com.evil.io` return `None`, and `www.instagram.com` returns `Platform.INSTAGRAM`.

---

### Step 1.5 — Fix silent MONTHLY fallback for unknown Stripe price IDs
**File:** `app/onboarding_session/services.py`

- [ ] First, confirm `PaymentCreateSchema.plan_type` is typed as `PlanType | None` (not required). If it isn't, update it first.

- [ ] In `_determine_plan_type` (around line 1744), replace the final line:
  ```python
  # Before
  return PlanType.MONTHLY

  # After
  return None
  ```

- [ ] Verify: send a webhook with an unrecognized `price_id` and confirm the payment record is saved with `plan_type=None`, not `MONTHLY`.

---

### Step 1.6 — Fix race condition in concurrent session creation
**File:** `app/onboarding_session/services.py`

- [ ] Add to the imports at the top of the file:
  ```python
  from sqlalchemy.exc import IntegrityError
  ```

- [ ] In `add_channels`, find the new session creation block (around line 192). Wrap the `self.db.add` + `flush` in a try/except:
  ```python
  # Before
  self.db.add(session)
  await self.db.flush()
  await self.db.refresh(session)
  return session

  # After
  try:
      self.db.add(session)
      await self.db.flush()
      await self.db.refresh(session)
  except IntegrityError:
      await self.db.rollback()
      raise OnboardingSessionAlreadyExists()
  return session
  ```

- [ ] Verify: fire two simultaneous requests with the same email. Exactly one session must be created; the second returns 400 `onboarding_session_already_exists`.

---

## Phase 1.7 — Replace raw httpx Clerk calls with SDK

**File:** `app/auth/services.py`

Two methods bypass the `clerk_client` SDK and make raw `httpx` requests directly to `api.clerk.com`. This is inconsistent, bypasses SDK-level retries/error handling, and manually manages auth headers.

---

### Step 1.7a — `_find_clerk_user_by_email` (line 108)

- [ ] Remove the `httpx` block:
  ```python
  async with httpx.AsyncClient() as client:
      response = await client.get(
          "https://api.clerk.com/v1/users",
          headers={"Authorization": f"Bearer {settings.CLERK_SECRET_KEY}"},
          params=[("email_address", email)],
      )
      ...
  ```
  Replace with:
  ```python
  from clerk_backend_api.models import GetUserListRequest

  users = await clerk_client.users.list_async(
      request=GetUserListRequest(email_address=[email])
  )
  return users[0].id if users else None
  ```
  Wrap in a `try/except` and raise `ClerkAuthenticationError` on SDK exceptions.

---

### Step 1.7b — `_verify_password` (line 148)

- [ ] Remove the `httpx` block:
  ```python
  async with httpx.AsyncClient() as client:
      response = await client.post(
          f"https://api.clerk.com/v1/users/{clerk_user_id}/verify_password",
          headers={...},
          json={"password": password},
      )
      ...
  ```
  Replace with:
  ```python
  result = await clerk_client.users.verify_password_async(
      user_id=clerk_user_id, password=password
  )
  if not result.verified:
      raise InvalidCredentials()
  return True
  ```
  Catch `SDKError`/`ClerkErrors` and map to `InvalidCredentials` or `ClerkAuthenticationError` as appropriate.

---

- [ ] Once both methods are migrated, remove the `import httpx` line from `app/auth/services.py` (it will be unused).
- [ ] Verify: run the sign-in flow end-to-end and confirm no raw HTTP calls hit `api.clerk.com` outside the SDK.

---

## Phase 2 — Important (Ship Within the Week)

Steps can be done in parallel by different people.

---

### Step 2.1 — Fix N+1 queries in stale session cleanup + remove internal commit from `delete_by_uuid`
**File:** `app/onboarding_session/services.py`

- [ ] Search the entire project for all callers of `delete_by_uuid` to confirm none rely on its internal commit outside of `clean_up_stale_onboarding_sessions`.

- [ ] Add `delete` to the existing SQLAlchemy import at the top of `services.py`:
  ```python
  from sqlalchemy import delete, func, or_, select
  ```

- [ ] In `delete_by_uuid` (around line 81), remove the `await self.db.commit()` line. The method should end with just:
  ```python
  if session:
      await self.db.delete(session)
  ```

- [ ] Replace the entire body of `clean_up_stale_onboarding_sessions` (around line 1786) with:
  ```python
  async def clean_up_stale_onboarding_sessions(self) -> None:
      """Clean up onboarding sessions stuck in PAGES step for over a week."""
      one_week_ago = datetime.now(timezone.utc) - timedelta(days=7)
      await self.db.execute(
          delete(OnboardingSessionModel).where(
              OnboardingSessionModel.current_step == OnboardingStep.PAGES,
              OnboardingSessionModel.created_at < one_week_ago,
          )
      )
  ```

- [ ] Verify: create stale test sessions, run the cleanup task, confirm deletion in a single DB round-trip.

---

### Step 2.2 — Remove hardcoded `2m.com` test artifact
**File:** `app/onboarding_session/services.py`

- [ ] Find and delete these two lines (around line 1124):
  ```python
  if parsed.netloc.lower() == "2m.com":
      add_trigger(channel_url, CustomQuoteTriggerFlag.HIGH_FOLLOWERS)
  ```

- [ ] Verify: submit `https://2m.com/page` as a channel URL and confirm it gets `UNSUPPORTED_PLATFORM`, not `HIGH_FOLLOWERS`.

---

### Step 2.3 — Reduce startup Redis ping timeout
**File:** `app/core/config.py`, `app/app.py`

- [ ] In `app/core/config.py`, add a dedicated Redis startup timeout (keep `STARTUP_STEP_TIMEOUT_SECONDS` for the DB ping):
  ```python
  STARTUP_REDIS_TIMEOUT_SECONDS: float = 5.0
  ```

- [ ] In `app/app.py`, update the Redis startup step (around line 318):
  ```python
  await _run_startup_step(
      step="redis_connect_ping",
      action=_startup_redis_ping,
      timeout_seconds=settings.STARTUP_REDIS_TIMEOUT_SECONDS,  # was STARTUP_STEP_TIMEOUT_SECONDS
      optional=True,
  )
  ```

---

### Step 2.4 — Fix N+1 queries in `add_channels` channel existence check
**File:** `app/onboarding_session/services.py`

Currently checks each URL with a separate DB query in a loop (around line 157):
```python
for url in new_channel_strs:
    if await channel_service.get_by_url(url):
        existing_urls.append(url)
```

- [ ] Add a batch method to `ChannelService` (or equivalent): `get_existing_urls(urls: list[str]) -> set[str]` using a single `WHERE url IN (...)` query.
- [ ] Replace the loop in `add_channels` with a single batch call.
- [ ] Verify: adding 5 channels triggers exactly 1 DB query for the existence check (check with SQL logging).

---

### Step 2.5 — Add expression indexes for case-insensitive email lookups
**File:** `app/onboarding_session/services.py` (query), migration file (new)

`get_by_email` uses `func.lower(column)` which prevents index use and causes full table scans (grows with prod data):
```python
func.lower(OnboardingSessionModel.email) == normalized_email
func.lower(OnboardingSessionModel.payment_email) == normalized_email
```

- [ ] Add a new Alembic migration with expression indexes:
  ```sql
  CREATE INDEX ix_onboarding_sessions_email_lower ON onboarding_sessions (LOWER(email));
  CREATE INDEX ix_onboarding_sessions_payment_email_lower ON onboarding_sessions (LOWER(payment_email));
  ```
- [ ] Verify with `EXPLAIN ANALYZE` on prod that the query uses the new indexes.

---

### Step 2.6 — Unify password validation across schemas
**File:** `app/onboarding_session/schemas.py`

- [ ] Extract the shared password validation into a module-level function above both classes:
  ```python
  def _validate_password_strength(v: str) -> str:
      if len(v) < 8:
          raise ValueError("Password must be at least 8 characters long")
      if not any(c.isupper() for c in v):
          raise ValueError("Password must contain at least one uppercase letter")
      if not any(c.islower() for c in v):
          raise ValueError("Password must contain at least one lowercase letter")
      if not any(c.isdigit() for c in v):
          raise ValueError("Password must contain at least one digit")
      special = "!@#$%^&*()_+-=[]{}|;:',.<>?/`~\"\\"
      if not any(c in special for c in v):
          raise ValueError("Password must contain at least one special character")
      return v
  ```

- [ ] Replace the `validate_password_strength` body in both `OnboardingSessionAccountSchema` and `AccountUpdateRequestSchema` with a single call to `_validate_password_strength(v)`.

- [ ] Verify: test both schemas with a password missing a special character — both must reject it with the same error message.

---

### Step 2.7 — Reduce Stripe API calls in `GET /payments/me`
**File:** `app/payment/services.py`

`GET /payments/me` is called by the non-admin dashboard on every page load. It currently makes up to 3 sequential Stripe API calls (~200–400ms each), keeping the HTTP connection open for 600ms–1200ms+.

**Partial fix already applied:** steps 2 and 3 are now parallelised with `asyncio.gather` (saves ~200–400ms).

**Remaining optimisation:** the dashboard only consumes three fields — `plan_type`, `amount`, and `next_billing_date`. The first two are already stored in `PaymentModel` and require no Stripe call. Only `next_billing_date` requires Stripe.

- [ ] In `get_payment_details_for_user`, serve `plan_type` and `amount` directly from the DB `payment` record instead of from Stripe.
- [ ] Skip `_create_customer_portal_url` on this code path — the dashboard page does not use `customer_portal_url`. Move portal URL creation to the `/dashboard/subscription` endpoint where it is actually needed.
- [ ] After the two removals, the only remaining Stripe call is `_get_subscription_details` (for `next_billing_date`). Total Stripe calls drops from 3 → 1, reducing p95 response time from ~800ms to ~200ms.
- [ ] Verify: load the non-admin dashboard and confirm `Current Plan`, price, and `Next Billing Date` still render correctly. Confirm `/dashboard/subscription` still shows the portal URL.

---

> **Note on auth httpx timeouts (PERFORMANCE_INVESTIGATION.md §3):** The raw `httpx` calls in `app/auth/services.py` also lack explicit timeouts. This is already addressed by Steps 1.7a/b (migrating to the Clerk SDK entirely). If 1.7a/b are delayed, add `timeout=httpx.Timeout(10.0)` to both `AsyncClient()` calls as a stopgap.

---

## Phase 3 — Cleanup (Single PR)

Batch all of these into one commit.

---

### Step 3.1 — Remove imports inside methods
**File:** `app/onboarding_session/services.py`

- [ ] Remove `from sqlalchemy import func` inside `get_by_email` (line ~85) — `func` is already imported at the top.
- [ ] Remove `import uuid as uuid_lib` inside `get_by_uuid` (line ~98) — add `import uuid as uuid_lib` to the module-level imports block at the top instead.

---

### Step 3.2 — Fix f-string logging in exception handlers
**File:** `app/onboarding_session/services.py` (lines ~905, 908, 910)

- [ ] Replace:
  ```python
  logger.error(f"Onboarding completion failed after Clerk user creation: {e}")
  logger.info(f"Rolled back Clerk user {clerk_user_id} due to completion failure")
  logger.error(f"Failed to rollback Clerk user {clerk_user_id}: {clerk_error}")
  ```
  With:
  ```python
  logger.error("Onboarding completion failed after Clerk user creation: %s", e)
  logger.info("Rolled back Clerk user %s due to completion failure", clerk_user_id)
  logger.error("Failed to rollback Clerk user %s: %s", clerk_user_id, clerk_error)
  ```

---

### Step 3.3 — Replace deprecated Pydantic `class Config`
**File:** `app/onboarding_session/schemas.py`

- [ ] Add `ConfigDict` to the existing pydantic import at line 4:
  ```python
  from pydantic import BaseModel, ConfigDict, EmailStr, Field, HttpUrl, field_validator, model_validator
  ```

- [ ] In `OnboardingSessionOutSchema`, replace:
  ```python
  class Config:
      from_attributes = True
  ```
  with:
  ```python
  model_config = ConfigDict(from_attributes=True)
  ```

---

### Step 3.4 — Remove unreachable `"www.snapchat.com"` from set
**File:** `app/onboarding_session/services.py` (line ~1691)

- [ ] Change:
  ```python
  if domain not in {"snapchat.com", "www.snapchat.com"}:
  ```
  to:
  ```python
  if domain != "snapchat.com":
  ```

---

### Step 3.5 — Remove unused `PaymentType` import
**File:** `app/onboarding_session/schemas.py`

- [ ] Remove line 7:
  ```python
  from app.payment.enums import PaymentType
  ```

---

### Step 3.6 — Rename misleading function
**File:** `app/onboarding_session/schemas.py`, `app/onboarding_session/router.py`

- [ ] Rename `get_empty_onboarding_session_data` → `get_empty_onboarding_session_response`.
- [ ] Update the import and call in `router.py` to match.
- [ ] Add a docstring clarifying it returns a partial shape that intentionally bypasses `OnboardingSessionOutSchema` validation.

---

### Step 3.7 — Rename timeout constant
**File:** `app/onboarding_session/services.py`

- [ ] Run: `grep -n "INSTAGRAM_USER_DETAILS_TIMEOUT_SECONDS" app/onboarding_session/services.py` to find all usages.
- [ ] Rename the class constant and all references to `SMS_API_TIMEOUT_SECONDS`.

---

### Step 3.8 — Fix comment typo
**File:** `app/onboarding_session/router.py` (line 568)

- [ ] Change:
  ```
  # Prefer a session-specific Stripe price id when available.nro
  ```
  to:
  ```
  # Prefer a session-specific Stripe price id when available.
  ```

---

## Execution Order

```
TODAY
  └── Run read-only SQL to check for existing plaintext passwords in production

WEEK 1 — Phase 1 (one commit per step, in order)
  ├── 1.1  Exclude password from DB          ← ship ASAP, security
  ├── 1.2  Idempotency guard
  ├── 1.3  Naive datetimes
  ├── 1.4  Platform domain matching
  ├── 1.5  Plan type fallback
  └── 1.6  Race condition guard

  → Deploy Phase 1 to staging, smoke test the full onboarding flow
  → Deploy to production
  → Run data remediation SQL if Step 1.1 assessment found existing passwords

WEEK 2 — Phase 2 (can parallelize)
  ├── 2.1  Bulk delete + remove internal commit
  ├── 2.2  Remove 2m.com artifact
  ├── 2.3  Redis startup timeout
  ├── 2.4  N+1 in add_channels channel existence check
  ├── 2.5  Expression indexes for email lookups
  ├── 2.6  Unify password validation
  └── 2.7  Reduce Stripe calls in GET /payments/me

WEEK 3 — Phase 3 (single cleanup PR)
  └── 3.1 → 3.8  All cleanup steps
```

> Steps 1.3 (async Clerk SDK), 2.2 (parallelize SMS calls), 2.4 (make /health async),
> 2.5 (DB pool config), and 3.9 (ClerkHTTPBearer investigation) are tracked separately
> in `SENIOR_FIX_PLAN.md`.
