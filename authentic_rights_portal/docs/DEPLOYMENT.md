# Deploying to Netlify

## Prerequisites

- Netlify account
- Git repo connected to Netlify (GitHub, GitLab, or Bitbucket)

## Build configuration

The repo includes a `netlify.toml` that sets:

- **Build command:** `npm run build`
- **Publish directory:** `.next`
- **Node version:** 20

Netlify auto-detects Next.js and uses the OpenNext adapter. No extra plugin is required.

## Environment variables

Set these in **Netlify Dashboard → Site settings → Environment variables** (or **Build & deploy → Environment**).

| Variable | Required | Description |
|----------|----------|-------------|
| `NEXT_PUBLIC_API_URL` | Yes | Backend API base URL (no trailing slash). Use: `https://mut3axhdpf.us-east-1.awsapprunner.com` |
| `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` | Yes | Clerk publishable key (from [Clerk Dashboard](https://dashboard.clerk.com)) |
| `CLERK_SECRET_KEY` | Yes | Clerk secret key (server-only; never exposed to the client) |

You can copy the values from your local `.env.local` for the same keys. **Do not commit `.env.local`**; it is gitignored.

### Scopes

- Set variables for **Production** (and optionally **Branch deploys** or **Deploy Previews** if you use them).
- Redeploy after changing env vars.

## Clerk configuration for production

In the [Clerk Dashboard](https://dashboard.clerk.com):

1. Add your Netlify site URL (e.g. `https://your-site.netlify.app`) under **Allowed redirect URLs** and **Sign-in/Sign-up URLs** if you use custom paths.
2. Ensure the same application’s **Publishable key** and **Secret key** are the ones you set in Netlify.

## Deploy

1. Push to the branch Netlify is watching (e.g. `main`).
2. Netlify runs `npm run build` and deploys the Next.js app.
3. The site will use `NEXT_PUBLIC_API_URL` for all API requests (onboarding, signup, custom quote, etc.).

## Backend base URL

The app expects the backend at:

- **Production:** `https://mut3axhdpf.us-east-1.awsapprunner.com`

Ensure this URL is reachable from the browser (CORS allowed for your Netlify domain) and from Netlify serverless/edge if you call the API from the server.
