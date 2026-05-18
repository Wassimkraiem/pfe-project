# Authentic Rights - Agent Guide

## Project Overview
FastAPI backend for a rights management platform. Uses Clerk for auth, Stripe for payments, PostgreSQL for data.
Web ECS task startup runs Alembic `upgrade head` before starting the app process.
- Startup now emits step-level INFO logs with `start`/`end`/`failed`, `duration_ms`, and per-step timeout values for: settings load, config fetch, DB ping, Redis ping, optional external checks, and optional DynamoDB check.
- Startup networking calls are guarded by strict timeouts from settings (`STARTUP_STEP_TIMEOUT_SECONDS`, `STARTUP_EXTERNAL_CHECK_TIMEOUT_SECONDS`, `STARTUP_DDB_CHECK_TIMEOUT_SECONDS`).
- Optional DynamoDB startup connectivity check is controlled via `STARTUP_ENABLE_DDB_CHECK` and uses `describe_table` with `DDB_TABLE_NAME`, `DDB_REGION` (or `AWS_REGION`/`AWS_DEFAULT_REGION`), and optional `DDB_ENDPOINT_URL`.

## Architecture
Each module follows: `router.py` → `services.py` → `model.py`
- **router**: HTTP handling only, uses `Depends()` for DI
- **services**: Business logic, async functions
- **model**: SQLAlchemy 2.0 models
- **schemas**: Pydantic v2 request/response models
- **exceptions**: Domain-specific errors

## Auth
- Authentication uses Clerk session JWTs. `POST /auth/signin` returns a `token`; send it as `Authorization: Bearer <token>`.
- `POST /onboarding_sessions/custom-quote/price` requires an authenticated Clerk token with `admin` role in JWT claims (`metadata.role`, `public_metadata.role`, or top-level `role`).
- `POST /canto/basic-group/remove` is currently unauthenticated for local testing and executes Canto removal directly (no Celery), returning the immediate result.
- `GET /onboarding_sessions/custom-quotes/pending` requires admin role; returns sessions where `custom_quote_submitted=true` and `price_id` is empty (null or ""), with top-level `channels` and `custom_quote_triggers` per item.
- `GET /onboarding_sessions/custom-quotes/status` requires admin role; returns `{ pending_payment, paid }` where `pending_payment` are sessions with price submitted but not yet paid, and `paid` are custom quote sessions that completed payment. Both lists include `service_agreement_signed_at` (if captured).

## Authenticated Endpoints
- `GET /users/me`
- `GET /users/me/overview`
- `POST /canto/basic-group/remove` (testing, no auth)
- `GET /canto/videos/{video_id}/download` (returns signed Canto download URL + records download event)
- `GET /library/downloads` (current user's paginated download history)
- `GET /channels`
- `GET /channels/{channel_id}`
- `POST /channels/{channel_id}`
- `DELETE /channels/{channel_id}`
- `GET /payments/me`
- `GET /payments/prices/{price_id}`

## Key Modules
| Module | Purpose |
|--------|---------|
| `auth/` | Clerk authentication, JWT verification (sign-in returns session JWT for Bearer auth) |
| `user/` | User profiles and management; `GET /users/me/overview` returns `{ user, payment, channels }` for the authenticated user |
| `channel/` | Channel/platform connections |
| `payment/` | Stripe subscriptions & webhooks (`Stripe-Signature` required); `GET /payments/me` returns payment details plus the Stripe customer portal URL for the authenticated user; `GET /payments/prices/{price_id}` returns `{ price, plan }` from Stripe (`plan` is `monthly`/`yearly`/`enterprise`) |
| `recommendation/` | Personalized recommendation events + feed (`POST /recommendations/events/search`, `POST /recommendations/events/click`, `GET /recommendations`) with profile signals stored in Postgres and candidate retrieval delegated to videos-search-api advanced-search |
| `onboarding_session/` | User onboarding flow |
| `custom_quote/` | Custom quote from onboarding session; `POST /custom-quotes/create` takes email only, fetches channels from onboarding session |
| `email/` | MJML email templates |
| `slack/` | Slack webhook notifications for quote submissions and payment completions |

## Background Jobs
- Celery is configured in `app/celery_app.py`.
- Redis is used as broker/result backend (`CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`).
- Broker connection has timeouts configured: `broker_connection_timeout=10s`, socket timeouts of 5-10s to prevent webhook handlers from hanging if Redis is unreachable.
- Async email sends are enqueued via tasks in `app/email/tasks.py` (setup-account, welcome, payment-success, payment-issue, custom-quote-created emails).
- Canto user provisioning is enqueued via `app/canto/tasks.py` after onboarding completion (basic plan group). **Canto tasks only execute in prod** (`ENV=prod`); in local/staging the task logs a skip message and returns early.
- Renewal access control also uses Canto tasks: users are removed from the basic-plan group when renewal grace expires and re-added automatically after successful renewal payment.
- After payment webhook processes successfully, user receives a payment-success email with link to complete account.
- All Celery tasks use retries: `autoretry_for=(ConnectionError, TimeoutError, OSError)`, exponential backoff (max 600s), up to 5 retries.
- Webhook task enqueue calls use `asyncio.wait_for` with 15s timeout to prevent blocking Stripe webhook responses.
- Payment Celery tasks run async DB work on a worker-process-local asyncio loop (instead of per-task `asyncio.run`) to avoid asyncpg/SQLAlchemy "Future attached to a different loop" errors.

## Webhook Security
- `POST /webhook` **requires** the `Stripe-Signature` header. Requests without it are rejected with 403.
- Signature is verified with Stripe's webhook signing mechanism using `STRIPE_WEBHOOK_SECRET`.
- If a payment webhook cannot be matched to an onboarding session, the endpoint returns an error (non-2xx) so Stripe retries instead of silently acknowledging.
- Renewal webhooks are handled asynchronously: `invoice.payment_failed` with `billing_reason=subscription_cycle` starts a grace window, and `invoice.payment_succeeded` with `billing_reason=subscription_cycle` clears failure state and restores access if suspended.

## Custom Quote
- Custom quote is also required if any Instagram, TikTok, YouTube, Facebook, Twitter/X, or Snapchat handle exceeds 2M followers (lookups via `app/sms_sdk.py`).
- If none of the provided channel URLs match supported platforms, `requires_custom_quote` is set to `true`.
- If follower counts are unavailable, the flow treats it as requiring a custom quote (no hard error).
- If SMS API calls fail (timeout, connection error, HTTP error), the channel triggers `SMS_API_ERROR` and routes to custom quote flow.
- `requires_custom_quote` is stored on `OnboardingSessionModel` and indicates the user is in the custom quote flow.
- `POST /onboarding_sessions/create-custom-quote` marks `custom_quote_submitted` as `true` and enqueues the custom-quote-created email.
- `POST /onboarding_sessions/custom-quote/price` sets `onboarding_sessions.price_id` for a custom-quote session; requires `custom_quote_submitted=true` and `payment_received=false`. After setting price, an email is sent to the user (code `CUSTOM_QUOTE_PRICE_SUBMITTED`) with a link to complete their subscription.
- When a custom quote is submitted, a team notification email is also sent to `CUSTOM_QUOTE_TEAM_EMAIL` with the submitter email, channels, and per-channel custom quote flags.
- `session_details.pages.custom_quote_triggers` stores per-channel trigger entries with `channel_url`, `flag`, and `message` (`HIGH_FOLLOWERS`, `UNKNOWN_FOLLOWER_COUNT`, `UNSUPPORTED_PLATFORM`, or `SMS_API_ERROR`).
- `GET /onboarding_sessions/custom-quotes/status` (admin) returns custom quotes grouped by payment status: `pending_payment` (price_id set, not paid) and `paid` (payment received). Each item includes top-level `channels` and `custom_quote_triggers`.
- When adding/removing channels, profile URLs are evaluated via SMS endpoints:
  - Instagram: `GET {SMS_BASE_URL}/instagram/user_details?handle=<handle>`
  - TikTok: `GET {SMS_BASE_URL}/tiktok/user_details?handle=@<handle>&source=TOKAPI`
  - YouTube: `GET {SMS_BASE_URL}/youtube/channels/details?name=<name>`
  - Facebook: `GET {SMS_BASE_URL}/facebook/pages/details?url=<page_url>`
  - Twitter/X: `GET {SMS_BASE_URL}/twitter/users/details?handle=<handle>`
  - Snapchat: `GET {SMS_BASE_URL}/snapchat/users/details?handle=<handle>`
- Adding channels to onboarding rejects URLs that already exist in the `channels` table.
- When channels are created during onboarding completion, SMS lookups populate `username` and `follower_count` and set `verification_status` to `verified` when successful.

## Checkout & Signature
- User enters signature before loading checkout URL.
- `POST /onboarding_sessions/checkout` requires `signature: str` and optional `plan` (`monthly` | `yearly`), `embedded` (bool, default true) in request body.
- **Embedded checkout** (`embedded: true`): Uses Stripe `ui_mode='embedded'`; response includes `client_secret` for mounting checkout in-page via Stripe.js. `return_url` redirects to `{FRONTEND_URL}/return?session_id={CHECKOUT_SESSION_ID}&onboarding_session={uuid}` after payment.
- Checkout uses `onboarding_sessions.price_id` when present; otherwise plan maps to Stripe `price_id`.
- With session `price_id`, checkout uses line-item quantity `1` (no channel-count multiplication). Without session `price_id`, quantity is the number of channels.
- If `onboarding_sessions.price_id` is set, checkout plan selection is locked and requests that explicitly send `plan` are rejected.
- Checkout pre-fills `customer_email`, but users can still edit it in Stripe Checkout.
- Checkout metadata includes `onboarding_session_uuid`, `channels`, `signature`, and `service_agreement_signed_at` (ISO timestamp captured when signature is submitted).
- Webhook payment processing listens to `checkout.session.completed` and `invoice.payment_succeeded`.
- Invoice events with `billing_reason=subscription_cycle` (renewals) or `billing_reason=subscription_create` (initial subscription) are ignored since `checkout.session.completed` handles initial payment with proper metadata. This prevents race conditions and avoids 1-hour Stripe retry delays.
- Webhook updates never downgrade onboarding from `completed` back to `account`.
- When `onboarding_session_uuid` is present in webhook metadata, lookup tries UUID first, then falls back to email lookup. If both fail, error is raised (no fallback session creation).
- Webhook payer email and signature are stored in `session_details.checkout`; `service_agreement_signed_at` is preserved there as well. If the payer email differs, the onboarding session email is updated.
- Payer email is also stored on `OnboardingSessionModel.payment_email` and email lookups match either `email` or `payment_email`.
- Payment signature and `service_agreement_signed_at` are stored on the payment record.
- Payment metadata saved to `payments.metadata` excludes `onboarding_session_uuid`.

## Pre-Payment Drop-Off Reminders
- Celery beat runs `email.periodics.send_pre_payment_reminder_email` every 15 minutes.
- First reminder goes out after 1 hour, then every 24 hours for up to 72 hours (max 3 sends).
- Reminders stop if payment is received or the account is created.
- Reminder throttling is tracked via `onboarding_emails` (code `PRE_PAYMENT_REMINDER`) and session-level `last_reminder_sent_at`/`reminders_count`.

## Account Setup Reminders
- Celery beat runs `email.periodics.send_account_setup_reminder_email` periodically.
- Targets sessions in ACCOUNT step, 1 hour after payment.
- Uses the `setup_account.mjml` template; link: `/signup?session_id={uuid}`.
- Reminder is sent once; tracked via `onboarding_emails` (code `ACCOUNT_SETUP_REMINDER`) and session-level `last_reminder_sent_at`/`reminders_count`.

## Already Paid (No Account) Email
- If a user enters an email that already has an active subscription but the account setup was never completed, the API enqueues the `already_paid_onboarding.mjml` email (code `ALREADY_PAID_ONBOARDING`) with a `/signup?session_id={uuid}` link to finish setup.
- When retrieving a session by email, the `ALREADY_PAID_ONBOARDING` email is sent to the email provided in the request.

## Welcome Email
- Sent after account creation completes (onboarding step COMPLETED).
- If `app/email/assets/get_started_guide.pdf` exists, it is attached as `BVIRAL_Get_Started_Guide.pdf`.

## Payment Confirmation Email
- Immediately after a successful payment (`checkout.session.completed` only; all subscription-related `invoice.payment_succeeded` events are skipped), the `send_payment_success_email_task` Celery task is enqueued with: `channels`, `amount_display`, `plan_label`, `signature`, `signed_at`, `customer_email`.
- The `payment_success.mjml` template renders in the email body: signatory details (email + signed-at), electronic signature block, numbered list of whitelisted channels, and fee breakdown (plan + amount).
- Payment confirmation emails are BCC'd to `PAYMENT_CONFIRMATION_BCC_EMAIL` (defaults to `records@bviral.com`) for record-keeping.
- If `app/email/assets/service_agreement.pdf` exists, the customer's signature is overlaid on the existing LICENSEE section (last page by default). The signed PDF is attached as `BVIRAL_Licensing_Agreement.pdf`.
- Signature position is configured via constants in `app/email/pdf.py`: `SIGNATURE_X`, `SIGNATURE_Y` (points from bottom-left), `SIGNATURE_PAGE_INDEX` (-1 for last page).
- The timestamp (`signed_at`) is rendered below the signature on the PDF overlay in ISO format with timezone (e.g., `2026-03-12T13:38:50 UTC`).
- Place a TTF signature/script font (Caveat) at `app/email/assets/signature_font.ttf`; falls back to Helvetica-Oblique if not present.
- PDF generation uses `pypdf` for merging and `reportlab` for creating the signature overlay.
- `EmailMessage` supports an `attachments: list[EmailAttachment]` field and optional `bcc: list[str]` field; `_build_mime_message` switches to `multipart/mixed` when attachments are present.

## Renewal Failure Handling
- Renewal failure state is tracked on `users` with `renewal_failed_at`, `renewal_grace_ends_at`, and `canto_access_suspended`.
- Grace period duration is configured by `RENEWAL_GRACE_PERIOD_MINUTES` (default `5` for local testing).
- The grace timer starts on the **first** renewal failure (`invoice.payment_failed` + `billing_reason=subscription_cycle`) and does not reset on repeated failed retries.
- When grace expires and payment is still unresolved, the worker marks `canto_access_suspended=true` and removes the user from Canto basic-plan group via `POST/DELETE /api/v1/groups/:groupId/users` payload `[email]`.
- On successful renewal payment (`invoice.payment_succeeded` + `billing_reason=subscription_cycle`), failure state is cleared and suspended users are re-added to the basic-plan group.
- Renewal Canto add/remove tasks are enqueued only when `settings.canto_enabled` is true; otherwise worker logs explicit skip messages and only DB suspension flags are updated.
- `GET /payments/me` now includes frontend signal fields: `renewal_failed`, `renewal_grace_ends_at`, and `canto_access_suspended`.
- `GET /payments/me` handles stale/invalid Stripe subscription IDs gracefully (logs warning and falls back to customer subscription lookup).

## Onboarding Email Tracking
- `OnboardingEmailModel` (in `app/email/models.py`) stores sent onboarding emails.
- Email codes: `PRE_PAYMENT_REMINDER`, `ACCOUNT_SETUP_REMINDER`, `ALREADY_PAID_ONBOARDING`, `CUSTOM_QUOTE_REQUEST`, `CUSTOM_QUOTE_PRICE_SUBMITTED`, `PAYMENT_CONFIRMATION`.
- Session-level reminder counters: `last_reminder_sent_at` (nullable), `reminders_count` (default 0).

## Slack Notifications
- Slack webhook notifications are sent via `app/slack/` module when `SLACK_WEBHOOK_URL` is configured.
- `settings.slack_enabled` returns `True` when `SLACK_WEBHOOK_URL` is non-empty (prod/staging only).
- `settings.slack_whitelisted_enabled` returns `True` when `SLACK_WEBHOOK_URL_WHITELISTED` is non-empty (prod/staging only).
- Celery tasks in `app/slack/tasks.py` use the same retry pattern as email tasks: `autoretry_for=(ConnectionError, TimeoutError, OSError)`, exponential backoff (max 600s), up to 5 retries.
- **Events that trigger Slack notifications:**
  - Custom quote submission (`POST /onboarding_sessions/create-custom-quote`): Sends notification with email, channels, and custom quote triggers (to `SLACK_WEBHOOK_URL`).
  - Payment completion (`checkout.session.completed` webhook):
    - **Subscription announcement** (to `SLACK_WEBHOOK_URL`): Celebration message with rate, term, date signed, customer name/email, and note that signed agreement PDF was sent via email.
    - **Whitelist notification** (to `SLACK_WEBHOOK_URL_WHITELISTED`): Lists all channel URLs to whitelist and record.
- Messages use Slack Block Kit for rich formatting.
- Slack notifications are non-critical; failures are logged but do not affect the main flow.

## Configuration
- **CORS**: `CORS_ORIGINS` (comma-separated) controls allowed frontend origins. Must be exact URLs (e.g. `https://authentic-rights-portal.netlify.app`); `*` is not allowed because `allow_credentials=True`. FastAPI CORS middleware reads this via `settings.cors_origins_list`.
- **SMS API**: `SMS_BASE_URL` plus optional `SMS_X_API_KEY` (sent as `x-api-key`) and `SMS_API_KEY` (sent as `Authorization: Bearer`).
- **Stripe customer portal**: `STRIPE_CUSTOMER_PORTAL_RETURN_URL` controls the billing portal return URL (defaults to `/dashboard/subscription` on the frontend domain).
- **Slack**: `SLACK_WEBHOOK_URL` is the Slack incoming webhook URL for general notifications. `SLACK_WEBHOOK_URL_WHITELISTED` is the webhook URL for the subscriptions-onboarding channel (whitelist & celebration announcements). Leave empty to disable respective notifications.

## Environment Configuration
- **ENV**: Controls environment mode. Valid values: `local`, `staging`, `prod`. Defaults to `local`.
- Helper properties on `settings`: `is_local`, `is_staging`, `is_prod`.
- **Canto**: User provisioning is only enabled in prod (`settings.canto_enabled`). Requires `ENV=prod` plus valid `CANTO_APP_ID` and `CANTO_APP_SECRET`. In non-prod, Canto tasks log a skip message and return early.
- `CANTO_BASIC_PLAN_GROUP_ID` can override the default basic-plan Canto group UUID used for add/remove access operations.
- **Sentry**: Error tracking is only enabled in prod (`settings.sentry_enabled`). Requires `ENV=prod` plus a valid `SENTRY_DSN`.
  - `SENTRY_DSN`: Sentry project DSN (empty to disable).
  - `SENTRY_TRACES_SAMPLE_RATE`: Performance tracing sample rate (0.0–1.0, default 1.0).
  - `SENTRY_PROFILES_SAMPLE_RATE`: Profiling sample rate (0.0–1.0, default 1.0).
  - Sentry SDK automatically integrates with FastAPI; `send_default_pii=True` captures request headers/IP for debugging.

## Health Checks
- `GET /health` returns basic liveness.
- `GET /health/db` checks DB connectivity and Alembic head vs current revision. Returns 200 if healthy, 503 otherwise.
- `GET /health` bypasses migration middleware so it stays lightweight even if startup migration work is slow.

## Database
- PostgreSQL with async driver
- Migrations: `alembic upgrade head`
- Session: use `get_async_session` dependency
- Alembic `env.py` must import all model modules (including `app.payment`) so autogenerate sees full metadata.
- Canto download tracking schema:
  - `downloaded_videos` table stores `user_id`, `video_id`, `video_title`, optional `thumbnail_url`, `source_scope`, `request_filters` (`JSONB`), and `downloaded_at`.
  - Enum type `cantodownloadsourcescope` currently supports `browse` and `detail`.
  - Added by migration `20260506_downloaded_videos`.
- Recommendation tables: `user_search_events`, `user_video_events`, `user_interest_profiles` are part of ORM metadata and must remain imported by Alembic env.
- Recommendation response `seed` includes `resolved_entities` (video-id signals enriched to title/categories/tags). Raw video IDs are not used as text `query_terms` for retrieval.
- Recommendation seed prioritizes recent `user_search_events` from DB (latest queries + parsed intent) and only falls back to profile aggregates, reducing stale/random recommendations.
- Recommendation ranking applies anti-repetition controls: suppression of recently seen/clicked/playlist videos, freshness bonus, category diversity cap, deterministic daily rotation, and a small exploration slice.
- Feature package `__init__.py` files should import ORM models (e.g., `app.payment.__init__` imports `PaymentModel`) so Alembic autogenerate sees tables.

## Commands
```bash
# Run locally
docker-compose -f docker-compose.local.yml up

# New migration
alembic revision --autogenerate -m "description"
```

## Architecture Diagrams
- Recommendation use-case: `docs/recommendation-system-usecase.mmd`
- Search use-case: `docs/search-system-usecase.mmd`

## CI/CD
- Bitbucket pipeline (`bitbucket-pipelines.yml`) runs on push to `main` or `staging`. Builds Docker image and pushes to ECR via `atlassian/aws-ecr-push-image` pipe (no OIDC).
- Pipelines use Bitbucket-hosted runners (do not set `runs-on` labels unless self-hosted runners are configured and online).
- **Required Bitbucket repo variables** (secured): `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_DEFAULT_REGION` (e.g. `eu-west-1`).
- Image tags: `{branch}` and `build-{BITBUCKET_BUILD_NUMBER}`. App Runner or other deploy is done outside this repo.
- Pipeline flow now includes Terraform apply for SSM/task-definition updates before image deploy and ECS service rollout.
- ECS rollout order is web first (wait until stable), then worker, to reduce migration/schema race risk.
- ECS deploy step expects `ECS_WORKER_SERVICE` only. `ECS_CLUSTER_NAME` defaults to `cluster-{ENV}`.

## Terraform SSM/ECS
- SSM parameters for ECS task secret injection are stored under `/bviral/authentic_rights_api/{ENV}/...`.
- **Store params / values**: Local apply uses `ssm_store/staging.tfvars` (gitignored; copy from `ssm_store/staging.tfvars.example` and fill). CI builds `.tfvars` from `ssm_store/.tfvars.tmpl` via `envsubst`; set Bitbucket repo variables to match.
- `ssm_store/parameters.tf` uses a single map + `for_each` pattern; add new env vars by updating `variables.tf`, the map in `parameters.tf`, and `ssm_store/.tfvars.tmpl`.
- ECS task definitions in `ssm_store/task_definition_*.tf` use image `authentic_rights_api` and run FastAPI web via `alembic upgrade head && gunicorn app.app:app -k uvicorn.workers.UvicornWorker` plus Celery worker with `app.celery_app:celery_app`.
- DynamoDB startup-check env vars are wired through SSM/Terraform: `STARTUP_ENABLE_DDB_CHECK`, `DDB_TABLE_NAME`, and `DDB_REGION`.

## Rules
- Type hints required on all functions
- Use `logging` module, never `print`
- Keep transactions short, no external API calls inside them
- Tests go in a `tests/` directory mirroring `app/` structure
- **Error handling**: Always use `AppError` subclasses with specific `error_code` (e.g. `user_already_exists`, `invalid_webhook_signature`). Never use raw `HTTPException` for client errors—use domain exceptions so responses include the proper error code for frontend handling.


always update agents.md whenever a new feature or anything important and not wrong is added and remove it when a i revert the changes 
