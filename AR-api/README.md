# Authentic Rights API

A FastAPI-based backend application for managing user onboarding, social media channels, and custom quotes.

## Table of Contents

- [Features](#features)
- [Tech Stack](#tech-stack)
- [Prerequisites](#prerequisites)
- [Getting Started](#getting-started)
- [Database Migrations](#database-migrations)
- [API Documentation](#api-documentation)
- [Project Structure](#project-structure)
- [API Endpoints](#api-endpoints)

## Features

- **User Management**: Create and manage user accounts with Clerk authentication
- **Onboarding Sessions**: Complete onboarding flow with payment integration
- **Channel Management**: Handle social media channel URLs (Instagram, YouTube, TikTok, Facebook)
- **Payment Integration**: Stripe subscription payments with webhook handling
- **Custom Quotes**: Generate and manage custom quotes linked to users and their channels

## Tech Stack

- **Framework**: FastAPI
- **Database**: PostgreSQL (via asyncpg)
- **ORM**: SQLAlchemy 2.0 (async)
- **Migrations**: Alembic
- **Container**: Docker & Docker Compose
- **Background Jobs**: Celery + Redis broker
- **Python**: 3.12+

## Prerequisites

- Docker and Docker Compose installed
- Git (for version control)

## Getting Started

### 1. Clone the Repository

```bash
git clone <your-bitbucket-repo-url>
cd Authentic_Rights
```

### 2. Configure Environment Variables

The application uses a `.env` file for configuration. A template is provided:

```bash
# Copy the example file
cp .env.example .env

# Edit .env and update the values (especially passwords!)
nano .env  # or use your preferred editor
```

**Important Configuration Variables:**

```env
# Database connection for the API
DATABASE_URL=postgresql+asyncpg://postgres:your_password@db:5432/authentic_rights

# PostgreSQL credentials
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_secure_password_here
POSTGRES_DB=authentic_rights

# Application settings
PROJECT_NAME=Authentic Rights API

# Frontend URL for redirects after payment
FRONTEND_URL=http://localhost:3000

# Stripe Payment Integration
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PRICE_ID_MONTHLY=price_monthly_...
STRIPE_PRICE_ID_YEARLY=price_yearly_...

# Clerk Authentication
CLERK_SECRET_KEY=your_clerk_secret_key
```

⚠️ **Security Notes:**
- Never commit `.env` to git (it's in `.gitignore`)
- Use strong, unique passwords
- Change default passwords before deploying to production
- Keep `.env.example` updated when adding new variables

### 3. Start the Application

The application uses Docker Compose for easy setup. Run:

```bash
docker compose -f docker-compose.local.yml up -d --build
```

This will:
- Start the PostgreSQL database
- Start Redis (message broker)
- Start the FastAPI application
- Start a Celery worker for async tasks (emails)
- Expose the API on `http://localhost:8000`

### 3. Verify the Application is Running

```bash
# Check container status
docker compose -f docker-compose.local.yml ps

# View logs
docker compose -f docker-compose.local.yml logs -f api
```

### 4. Access the API

- **API Base URL**: `http://localhost:8000`
- **Health Check**: `http://localhost:8000/health`

## Database Migrations

### Running Migrations

The project uses Alembic for database migrations.

#### Apply All Pending Migrations

```bash
docker compose -f docker-compose.local.yml exec api alembic upgrade head
```

#### Check Current Migration Version

```bash
docker compose -f docker-compose.local.yml exec api alembic current
```

#### View Migration History

```bash
docker compose -f docker-compose.local.yml exec api alembic history
```

### Creating New Migrations

When you modify models, generate a new migration:

```bash
docker compose -f docker-compose.local.yml exec api alembic revision --autogenerate -m "description of changes"
```

Then apply it:

```bash
docker compose -f docker-compose.local.yml exec api alembic upgrade head
```

### Rolling Back Migrations

Downgrade to previous version:

```bash
docker compose -f docker-compose.local.yml exec api alembic downgrade -1
```

Downgrade to specific version:

```bash
docker compose -f docker-compose.local.yml exec api alembic downgrade <revision_id>
```

## API Documentation

### Swagger UI (Interactive Documentation)

Access the interactive API documentation at:

**🔗 http://localhost:8000/docs**

Features:
- Browse all available endpoints
- View request/response schemas
- Test API calls directly from the browser
- See detailed endpoint documentation

### ReDoc (Alternative Documentation)

Alternative documentation format available at:

**🔗 http://localhost:8000/redoc**

### OpenAPI Schema

Raw OpenAPI JSON schema:

**🔗 http://localhost:8000/openapi.json**

## Project Structure

```
Authentic_Rights/
├── alembic/                    # Database migrations
│   ├── versions/              # Migration files
│   └── env.py                 # Alembic configuration
├── app/
│   ├── channel/               # Channel management module
│   │   ├── channel.py         # Channel model
│   │   ├── router.py          # Channel endpoints
│   │   ├── schemas.py         # Pydantic schemas
│   │   ├── services.py        # Business logic
│   │   ├── dependencies.py    # FastAPI dependencies
│   │   ├── exceptions.py      # Custom exceptions
│   │   └── enums.py           # Enumerations
│   ├── customQuote/           # Custom quote module
│   │   ├── custom_quote.py    # CustomQuote model
│   │   ├── router.py          # Quote endpoints
│   │   ├── schemas.py         # Pydantic schemas
│   │   ├── services.py        # Business logic
│   │   ├── dependencies.py    # FastAPI dependencies
│   │   └── exceptions.py      # Custom exceptions
│   ├── onBoardingSession/     # Onboarding session module
│   │   ├── onboarding_session.py  # OnboardingSession model
│   │   ├── router.py          # Onboarding endpoints
│   │   ├── schemas.py         # Pydantic schemas
│   │   ├── services.py        # Business logic
│   │   ├── dependencies.py    # FastAPI dependencies
│   │   ├── exceptions.py      # Custom exceptions
│   │   └── enums.py           # OnboardingStep enum
│   ├── user/                  # User management module
│   │   ├── user.py            # User model
│   │   ├── router.py          # User endpoints
│   │   ├── schemas.py         # Pydantic schemas
│   │   ├── services.py        # Business logic
│   │   └── enums.py           # User enumerations
│   ├── core/                  # Core configuration
│   │   └── config.py          # Application settings
│   ├── db/                    # Database setup
│   │   ├── base.py            # SQLAlchemy base
│   │   ├── database.py        # Database connection
│   │   └── session.py         # Session management
│   ├── exceptionhandler.py    # Global exception handling
│   ├── response.py            # Standard response format
│   └── app.py                 # FastAPI application entry point
├── docker-compose.local.yml   # Docker Compose configuration
├── Dockerfile                 # Docker image definition
├── requirements.txt           # Python dependencies
├── alembic.ini               # Alembic configuration
└── README.md                  # This file
```

## API Endpoints

### Onboarding Session

- `POST /onboarding_sessions/get-session-by-email` - Get session by email
- `GET /onboarding_sessions/{session_uuid}` - Get session by UUID
- `POST /onboarding_sessions/channels/add` - Add channel URLs (creates session if new)
- `POST /onboarding_sessions/channels/remove` - Remove a channel URL
- `POST /onboarding_sessions/checkout` - Create Stripe checkout link
- `POST /onboarding_sessions/{session_uuid}/complete` - Complete onboarding with account details

### Payment Webhooks

- `POST /webhooks` - Handle Stripe webhook events (payment confirmation)

### Custom Quotes

- `POST /custom-quotes` - Create custom quote from onboarding session
- `GET /custom-quotes/{quote_id}` - Get quote by ID
- `GET /custom-quotes` - List all quotes
- `POST /custom-quotes/{quote_id}` - Update quote
- `DELETE /custom-quotes/{quote_id}` - Delete quote

### Channels

- `POST /channels` - Create a new channel
- `GET /channels/{channel_id}` - Get channel by ID
- `GET /channels` - List channels (filterable by user_id)
- `POST /channels/{channel_id}` - Update channel
- `DELETE /channels/{channel_id}` - Delete channel

### Users

- `POST /users` - Create a new user
- `GET /users` - List all users

### Health Check

- `GET /health` - Check API health status

## Development Commands

### Stop the Application

```bash
docker compose -f docker-compose.local.yml down
```

### Restart the Application

```bash
docker compose -f docker-compose.local.yml restart
```

### View Application Logs

```bash
docker compose -f docker-compose.local.yml logs -f api
```

### Access Database Directly

```bash
docker compose -f docker-compose.local.yml exec db psql -U postgres -d authentic_rights
```

### Rebuild Containers

If you make changes to `requirements.txt` or `Dockerfile`:

```bash
docker compose -f docker-compose.local.yml up --build -d
```

## Onboarding Flow

The onboarding process follows these steps:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           ONBOARDING FLOW                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  1. ADD CHANNELS (PAGES step)                                               │
│     POST /onboarding_sessions/channels/add                                  │
│     └─> Creates session with channel URLs                                   │
│                                                                             │
│  2. CREATE CHECKOUT                                                         │
│     POST /onboarding_sessions/checkout                                      │
│     └─> Returns Stripe checkout URL                                         │
│                                                                             │
│  3. USER PAYS ON STRIPE                                                     │
│     └─> Webhook received at POST /webhooks                                  │
│     └─> Session moves to ACCOUNT step                                       │
│     └─> User redirected to: {FRONTEND_URL}/signup/?session_id={session_uuid}          │
│                                                                             │
│  4. COMPLETE ONBOARDING                                                     │
│     POST /onboarding_sessions/{session_uuid}/complete                       │
│     └─> Creates: User (Clerk + DB), Channels, Payment record               │
│     └─> Session marked as COMPLETED                                         │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Example API Usage

### 1. Add Channels (Start Onboarding)

```bash
curl -X POST "http://localhost:8000/onboarding_sessions/channels/add" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "channels": [
      "https://instagram.com/username",
      "https://youtube.com/@channel"
    ]
  }'
```

### 2. Create Checkout Link

```bash
curl -X POST "http://localhost:8000/onboarding_sessions/checkout" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "plan": "monthly",
    "payment_flow_type": "subscription"
  }'
```

**Plan options:** `monthly` or `yearly`

**Response:**
```json
{
  "status_code": 200,
  "message": "success",
  "data": {
    "checkout_url": "https://checkout.stripe.com/...",
    "channels_count": 2,
    "payment_flow_type": "subscription"
  }
}
```

### 3. Get Session by UUID (After Payment Redirect)

```bash
curl -X GET "http://localhost:8000/onboarding_sessions/550e8400-e29b-41d4-a716-446655440000"
```

### 4. Complete Onboarding

```bash
curl -X POST "http://localhost:8000/onboarding_sessions/550e8400-e29b-41d4-a716-446655440000/complete" \
  -H "Content-Type: application/json" \
  -d '{
    "first_name": "John",
    "last_name": "Doe",
    "account_type": "individual",
    "password": "SecurePass123!",
    "confirm_password": "SecurePass123!"
  }'
```

**Response:**
```json
{
  "status_code": 200,
  "message": "success",
  "data": {
    "message": "Onboarding completed successfully",
    "user_id": 1,
    "channels_created": 2,
    "payment_id": 1
  }
}
```

## Environment Variables

All configuration is done through the `.env` file:

### Required Variables:

| Variable | Description | Example |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string for asyncpg | `postgresql+asyncpg://user:pass@db:5432/dbname` |
| `POSTGRES_USER` | PostgreSQL username | `postgres` |
| `POSTGRES_PASSWORD` | PostgreSQL password | `secure_password_123` |
| `POSTGRES_DB` | PostgreSQL database name | `authentic_rights` |
| `STRIPE_SECRET_KEY` | Stripe secret key | `sk_test_xxx...` |
| `STRIPE_WEBHOOK_SECRET` | Secret for webhook signature verification | `whsec_xxx...` |
| `STRIPE_PRICE_ID_MONTHLY` | Stripe monthly plan price ID | `price_xxx...` |
| `STRIPE_PRICE_ID_YEARLY` | Stripe yearly plan price ID | `price_xxx...` |
| `CLERK_SECRET_KEY` | Clerk authentication secret key | `sk_test_xxx...` |
| `CELERY_BROKER_URL` | Redis broker URL for Celery | `redis://redis:6379/0` |
| `CELERY_RESULT_BACKEND` | Redis backend URL for Celery | `redis://redis:6379/1` |

### Optional Variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `PROJECT_NAME` | Application name | `Authentic Rights API` |
| `FRONTEND_URL` | Frontend URL for payment redirects | `http://localhost:3000` |
| `STRIPE_API_VERSION` | Optional Stripe API version override | *(empty)* |

### Celery Worker (optional manual run)

If you run the API outside Docker, start a worker separately:

```bash
celery -A app.celery_app.celery_app worker --loglevel=info
```

### Database URL Format:

```
postgresql+asyncpg://[user]:[password]@[host]:[port]/[database]
```

**Examples:**

```bash
# Docker (internal network)
DATABASE_URL=postgresql+asyncpg://postgres:mypassword@db:5432/authentic_rights

# Local PostgreSQL
DATABASE_URL=postgresql+asyncpg://postgres:mypassword@localhost:5432/authentic_rights

# Remote server
DATABASE_URL=postgresql+asyncpg://user:password@db.example.com:5432/dbname
```

## Troubleshooting

### Database Connection Issues

```bash
# Check if database is running
docker compose -f docker-compose.local.yml ps

# Restart database
docker compose -f docker-compose.local.yml restart db
```

### Migration Errors

```bash
# Check current migration status
docker compose -f docker-compose.local.yml exec api alembic current

# View detailed migration info
docker compose -f docker-compose.local.yml exec api alembic history --verbose
```

### Container Issues

```bash
# Remove all containers and volumes (⚠️ This will delete data!)
docker compose -f docker-compose.local.yml down -v

# Rebuild and start fresh
docker compose -f docker-compose.local.yml up --build -d
```

## Contributing

1. Create a new branch for your feature
2. Make your changes
3. Generate migrations if models changed
4. Test your changes
5. Commit and push to Bitbucket
6. Create a pull request

## License

[Your License Here]

## Support

For issues and questions, please contact [your-email@example.com]
