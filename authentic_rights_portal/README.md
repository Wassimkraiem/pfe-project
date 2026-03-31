# BVIRAL - Get Viral Clips

A subscription platform for accessing viral video content. Built with Next.js 16, React 19, and Material-UI (MUI).

## Table of Contents

- [Overview](#overview)
- [Tech Stack](#tech-stack)
- [Getting Started](#getting-started)
- [Project Structure](#project-structure)
- [Theme System](#theme-system)
- [Pages & Routing](#pages--routing)
- [Components](#components)
- [Styling Guidelines](#styling-guidelines)
- [Development Workflow](#development-workflow)

---

## Overview

BVIRAL is a content subscription platform that allows users to:

- **Subscribe** to access 90,000+ viral videos
- **Manage** their subscription and channels
- **Partner** with BVIRAL for custom enterprise quotes

### Key User Flows

1. **Signup Flow** (< 2M followers): Email → Add Channels → Checkout → Create Account
2. **Partner/Contact Flow** (> 2M followers): Email → Add Channels → Request Quote → Thank You
3. **Dashboard**: Manage subscription, view channels, get support, become affiliate

---

## Tech Stack

| Technology | Version | Purpose |
|------------|---------|---------|
| [Next.js](https://nextjs.org/) | 16.1.1 | React framework with App Router |
| [React](https://react.dev/) | 19.2.3 | UI library |
| [Material-UI (MUI)](https://mui.com/) | 7.3.7 | Component library |
| [Emotion](https://emotion.sh/) | 11.14.0 | CSS-in-JS (MUI styling) |
| [Lucide React](https://lucide.dev/) | 0.562.0 | Icon library |
| [TypeScript](https://www.typescriptlang.org/) | 5.x | Type safety |

---

## Getting Started

### Prerequisites

- Node.js 18+ (recommended: 20+)
- npm, yarn, pnpm, or bun

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd getviralclips

# Install dependencies
npm install

# Start development server
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) to view the app.

### Available Scripts

| Command | Description |
|---------|-------------|
| `npm run dev` | Start development server |
| `npm run build` | Build for production |
| `npm run start` | Start production server |
| `npm run lint` | Run ESLint |
| `npm run format` | Format code with Prettier |
| `npm run format:check` | Check formatting without changes |

---

## Project Structure

```
src/
├── app/                      # Next.js App Router pages
│   ├── layout.tsx            # Root layout (ThemeRegistry, Header)
│   ├── page.tsx              # Homepage (pricing)
│   ├── globals.css           # Global CSS reset
│   │
│   ├── signup/               # Signup flow (< 2M followers)
│   │   ├── page.tsx          # Step 1: Email
│   │   ├── pages/page.tsx    # Step 2: Add Channels
│   │   ├── checkout/page.tsx # Step 3: Payment (Stripe placeholder)
│   │   └── account/page.tsx  # Step 4: Create Account
│   │
│   ├── contact/              # Partner flow (> 2M followers)
│   │   ├── page.tsx          # Step 1: Email
│   │   ├── pages/page.tsx    # Step 2: Add Channels
│   │   └── quote/
│   │       ├── page.tsx      # Step 3: Review & Submit
│   │       └── thank-you/page.tsx  # Confirmation
│   │
│   └── dashboard/            # User dashboard (authenticated)
│       ├── layout.tsx        # Dashboard layout with sidebar
│       ├── page.tsx          # Dashboard home
│       ├── subscription/page.tsx  # Manage subscription
│       ├── support/page.tsx  # Help & FAQ
│       └── affiliate/page.tsx # Affiliate program
│
├── components/               # Reusable components
│   ├── Header.tsx            # Main navigation header
│   ├── ConditionalHeader.tsx # Shows/hides header based on route
│   ├── DashboardSidebar.tsx  # Dashboard navigation sidebar
│   └── StepIndicator.tsx     # Multi-step progress indicator
│
└── theme/                    # MUI Theme configuration
    ├── index.ts              # Main theme export
    ├── palette.ts            # Color definitions
    ├── typography.ts         # Font & text styles
    ├── components.ts         # Component overrides
    └── ThemeRegistry.tsx     # Theme provider wrapper
```

---

## Theme System

The app uses a custom MUI theme located in `src/theme/`. This ensures consistent styling across all components.

### Color Palette (`palette.ts`)

```typescript
// Primary colors
primary: "#4D8AFF"      // Main blue - buttons, links, accents
primaryDark: "#3D7AEF"  // Hover state

// Secondary colors (dark buttons)
secondary: "#111827"    // Dark/black buttons
secondaryDark: "#1f2937"

// Text colors
textPrimary: "#111827"    // Headings, main text
textSecondary: "#6b7280"  // Descriptions, muted text

// Status colors
error: "#ef4444"        // Red - errors, cancel buttons, inactive
success: "#10b981"      // Green - success states
warning: "#f97316"      // Orange - growth indicators

// Backgrounds
background: "#ffffff"   // Default
subtle: "#fafafa"       // Dashboard background
muted: "#f9fafb"        // Alternate background

// Borders
borderLight: "#e5e7eb"  // Card borders
borderMain: "#d1d5db"   // Input borders, dividers
```

### Typography (`typography.ts`)

- **Font Family**: Geist Sans (loaded via `next/font`)
- **Headings (h1-h6)**: Bold (700 weight)
- **Body text**: Regular weight, good line heights
- **Buttons**: Semi-bold (600 weight), no text transform

### Component Overrides (`components.ts`)

Pre-configured styles for MUI components:

| Component | Key Styles |
|-----------|------------|
| `Button` | No elevation, rounded corners, custom disabled states |
| `Card` | No shadow, subtle border, 12px border radius |
| `Chip` | Status badges (Active, Pending, Premium, etc.) |
| `TextField` | Blue focus state, rounded corners |
| `Tabs` | Pill-style tabs with gray background |
| `Table` | Clean styling with hover states |

### Using the Theme

The theme is automatically applied via `ThemeRegistry` in the root layout. Access theme values in components:

```tsx
import { Box, Button, Typography } from "@mui/material";

// Use sx prop for styling
<Box sx={{ bgcolor: "primary.main", color: "text.secondary" }}>
  <Typography variant="h4" fontWeight="bold">Title</Typography>
  <Button variant="contained" color="primary">Click Me</Button>
</Box>
```

---

## Pages & Routing

### Public Pages

| Route | Description |
|-------|-------------|
| `/` | Homepage with pricing cards |
| `/signup` | Signup Step 1 - Email |
| `/signup/pages` | Signup Step 2 - Add Channels |
| `/signup/checkout` | Signup Step 3 - Payment |
| `/signup/account` | Signup Step 4 - Create Account |
| `/contact` | Partner Step 1 - Email |
| `/contact/pages` | Partner Step 2 - Add Channels |
| `/contact/quote` | Partner Step 3 - Review & Submit |
| `/contact/quote/thank-you` | Partner confirmation |

### Protected Pages (Dashboard)

| Route | Description |
|-------|-------------|
| `/dashboard` | Main dashboard |
| `/dashboard/subscription` | Manage subscription |
| `/dashboard/support` | Help & FAQ |
| `/dashboard/affiliate` | Affiliate program |

### Header Visibility

The header is hidden on dashboard pages. This is controlled by `ConditionalHeader.tsx`:

```tsx
// Header hidden on these paths:
const hideHeaderPaths = ["/dashboard"];
```

---

## Components

### StepIndicator

Multi-step progress indicator used in signup and contact flows.

```tsx
import StepIndicator from "@/components/StepIndicator";

const steps = [
  { number: 1, label: "Email" },
  { number: 2, label: "Pages" },
  { number: 3, label: "Checkout" },
  { number: 4, label: "Account" },
];

<StepIndicator steps={steps} currentStep={2} />
```

**Props:**
- `steps`: Array of `{ number: number, label: string }`
- `currentStep`: Current active step number

### Header

Main navigation with logo and menu items. Responsive with mobile hamburger menu.

### DashboardSidebar

Navigation sidebar for dashboard pages. Shows:
- Logo and user name
- Navigation links (Dashboard, Manage Subscription, Support, Affiliate)
- Sign Out button

Active state is automatically determined based on current route.

---

## Styling Guidelines

### Preferred Approach: MUI sx Prop

Use the `sx` prop for component-specific styles:

```tsx
<Box
  sx={{
    display: "flex",
    flexDirection: { xs: "column", sm: "row" },  // Responsive
    gap: 2,
    p: { xs: 2, sm: 3 },
    bgcolor: "#fafafa",
    borderRadius: 3,
    border: "1px solid #e5e7eb",
  }}
>
```

### Responsive Breakpoints

```tsx
// MUI breakpoints (defined in theme)
xs: 0      // Mobile
sm: 640    // Tablet
md: 768    // Small desktop
lg: 1024   // Desktop
xl: 1280   // Large desktop

// Usage
sx={{
  fontSize: { xs: "1rem", sm: "1.25rem", md: "1.5rem" },
  display: { xs: "none", md: "block" },
}}
```

### Common Patterns

**Card Component:**
```tsx
<Card sx={{ borderRadius: 3, boxShadow: "none", border: "1px solid #e5e7eb" }}>
  <CardContent sx={{ p: 3 }}>
    {/* Content */}
  </CardContent>
</Card>
```

**Primary Button:**
```tsx
<Button
  variant="contained"
  sx={{
    bgcolor: "#4D8AFF",
    "&:hover": { bgcolor: "#3D7AEF" },
    textTransform: "none",
    fontWeight: 600,
    borderRadius: "9999px",  // Pill shape
  }}
>
  Get Started
</Button>
```

**Outlined Button:**
```tsx
<Button
  variant="outlined"
  sx={{
    borderColor: "#d1d5db",
    color: "#111827",
    textTransform: "none",
    fontWeight: 600,
    borderRadius: "9999px",
    "&:hover": { bgcolor: "#f9fafb", borderColor: "#d1d5db" },
  }}
>
  Back
</Button>
```

**Status Chip:**
```tsx
// Active (dark)
<Chip label="Active" size="small" sx={{ bgcolor: "#111827", color: "white" }} />

// Inactive (red)
<Chip label="Inactive" size="small" sx={{ bgcolor: "#ef4444", color: "white" }} />

// Pending (gray)
<Chip label="Pending" size="small" sx={{ bgcolor: "#f3f4f6", color: "#4b5563" }} />
```

### Icons

Use Lucide React for icons:

```tsx
import { ArrowRight, Check, Globe, User } from "lucide-react";

<ArrowRight style={{ width: 16, height: 16 }} />
<Check style={{ width: 20, height: 20, color: "#4D8AFF" }} />
```

---

## Development Workflow

### Adding a New Page

1. Create file in `src/app/[route]/page.tsx`
2. Add `"use client"` directive if using hooks/state
3. Import MUI components and icons as needed
4. Follow existing patterns for layout and styling

### Modifying the Theme

1. Edit files in `src/theme/`
2. Changes apply globally via `ThemeRegistry`
3. Test across multiple pages to ensure consistency

### Code Quality

```bash
# Before committing
npm run format      # Auto-fix formatting
npm run lint        # Check for errors
npm run build       # Verify production build
```

### File Naming Conventions

- **Pages**: `page.tsx` (Next.js App Router convention)
- **Layouts**: `layout.tsx`
- **Components**: PascalCase (e.g., `StepIndicator.tsx`)
- **Theme files**: camelCase (e.g., `palette.ts`)

---

## Notes for Future Development

### Authentication

Currently using mock data. Integrate with your auth provider:
- Replace mock user data in dashboard pages
- Add route protection middleware
- Implement sign in/sign out functionality

### Payment Integration

Stripe placeholder exists at `/signup/checkout`. To integrate:
- Add Stripe SDK
- Create payment intent API route
- Handle success/failure callbacks

### API Integration

Replace mock data with real API calls:
- User data in dashboard
- Subscription management

### State Management

Consider adding for complex state:
- React Context for user/auth state
- URL state for multi-step forms
- Server state with React Query or SWR

---

## Resources

- [Next.js Documentation](https://nextjs.org/docs)
- [MUI Documentation](https://mui.com/material-ui/getting-started/)
- [Lucide Icons](https://lucide.dev/icons)
- [Emotion Documentation](https://emotion.sh/docs/introduction)
