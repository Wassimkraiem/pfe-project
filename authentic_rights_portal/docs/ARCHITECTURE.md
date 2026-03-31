# Architecture Overview

This document explains the architectural decisions and patterns used in the BVIRAL application.

## Application Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Next.js App                          │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────┐   │
│  │                   Root Layout                        │   │
│  │  ┌─────────────┐  ┌────────────────────────────┐   │   │
│  │  │ ThemeRegistry│  │   ConditionalHeader        │   │   │
│  │  │   (MUI)      │  │   (shows/hides based on   │   │   │
│  │  │             │  │    current route)          │   │   │
│  │  └─────────────┘  └────────────────────────────┘   │   │
│  │                                                     │   │
│  │  ┌─────────────────────────────────────────────┐   │   │
│  │  │               <main>{children}</main>        │   │   │
│  │  │                                              │   │   │
│  │  │  ┌─────────────────┐ ┌─────────────────┐ │   │   │
│  │  │  │  Public Pages   │ │ Dashboard Pages │ │   │   │
│  │  │  └─────────────────┘ └─────────────────┘ │   │   │
│  │  └─────────────────────────────────────────────┘   │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

## Page Categories

### 1. Public Pages (with Header)

These pages show the main navigation header:

- `/` - Homepage
- `/signup/*` - Signup flow
- `/contact/*` - Partner/contact flow

### 2. Dashboard Pages (with Sidebar)

These pages use a sidebar layout and hide the main header:

```
┌────────────────────────────────────────────────────┐
│ ┌──────────┐  ┌─────────────────────────────────┐ │
│ │          │  │                                 │ │
│ │ Sidebar  │  │         Page Content            │ │
│ │          │  │                                 │ │
│ │ - Logo   │  │                                 │ │
│ │ - Nav    │  │                                 │ │
│ │ - Sign   │  │                                 │ │
│ │   Out    │  │                                 │ │
│ └──────────┘  └─────────────────────────────────┘ │
└────────────────────────────────────────────────────┘
```

Dashboard has its own `layout.tsx` that includes `DashboardSidebar`.

## Component Hierarchy

```
RootLayout
├── ThemeRegistry (MUI Theme Provider)
│   ├── CssBaseline (MUI reset)
│   └── children
├── ConditionalHeader
│   └── Header (conditionally rendered)
└── <main>
    └── Page Components
```

## Data Flow Patterns

### Current (Mock Data)

```typescript
// Mock data defined in component
const mockUser = {
  firstName: "john",
  plan: "Business-Pro",
  // ...
};

// Used directly in component
<Typography>Welcome back, {mockUser.firstName}!</Typography>
```

### Future (API Integration)

```typescript
// Fetch data from API
const { data: user, isLoading } = useQuery({
  queryKey: ['user'],
  queryFn: fetchUser,
});

// Handle loading state
if (isLoading) return <Skeleton />;

// Use data
<Typography>Welcome back, {user.firstName}!</Typography>
```

## Multi-Step Form Pattern

Both signup and contact flows use a multi-step pattern:

```
Step 1 (Email) → Step 2 (Channels) → Step 3 (Action) → [Step 4 / Thank You]
```

### Navigation Between Steps

```typescript
// Using Next.js Link for navigation
<Button component={Link} href="/signup/pages">
  Continue
</Button>

// Using router for programmatic navigation
const router = useRouter();
router.push("/dashboard");
```

### Step Indicator

Each step page includes a `StepIndicator` showing progress:

```typescript
const steps = [
  { number: 1, label: "Email" },
  { number: 2, label: "Pages" },
  { number: 3, label: "Checkout" },
  { number: 4, label: "Account" },
];

<StepIndicator steps={steps} currentStep={currentStep} />
```

## State Management

### Local State (useState)

Used for form inputs and UI state:

```typescript
const [email, setEmail] = useState("");
const [isSubmitting, setIsSubmitting] = useState(false);
```

### URL State (useSearchParams)

Used for passing data between pages:

```typescript
// Passing email to thank you page
router.push(`/contact/quote/thank-you?email=${encodeURIComponent(email)}`);

// Reading email on thank you page
const searchParams = useSearchParams();
const email = searchParams.get("email");
```

### Future Considerations

For more complex state:

1. **React Context** - User/auth state
2. **URL State** - Multi-step form data
3. **Server State** - React Query/SWR for API data

## Styling Architecture

### Theme-Based Styling

All styling flows from the MUI theme:

```
theme/
├── palette.ts      → Colors
├── typography.ts   → Fonts & text
├── components.ts   → Component defaults
└── index.ts        → Combines all
```

### Styling Priority

1. **Theme defaults** - Apply to all components
2. **sx prop** - Component-specific overrides
3. **style prop** - Inline styles (use sparingly)

### Responsive Design

All pages are mobile-first with responsive breakpoints:

```typescript
sx={{
  padding: { xs: 2, sm: 3, lg: 4 },      // Responsive padding
  display: { xs: "none", md: "block" },   // Show/hide
  fontSize: { xs: "1rem", sm: "1.25rem" } // Responsive text
}}
```

## Routing Structure

### Next.js App Router

```
app/
├── page.tsx                    → /
├── layout.tsx                  → Wraps all pages
│
├── signup/
│   ├── page.tsx                → /signup
│   ├── pages/page.tsx          → /signup/pages
│   ├── checkout/page.tsx       → /signup/checkout
│   └── account/page.tsx        → /signup/account
│
├── contact/
│   ├── page.tsx                → /contact
│   ├── pages/page.tsx          → /contact/pages
│   └── quote/
│       ├── page.tsx            → /contact/quote
│       └── thank-you/page.tsx  → /contact/quote/thank-you
│
└── dashboard/
    ├── layout.tsx              → Dashboard layout (sidebar)
    ├── page.tsx                → /dashboard
    ├── subscription/page.tsx   → /dashboard/subscription
    ├── support/page.tsx        → /dashboard/support
    └── affiliate/page.tsx      → /dashboard/affiliate
```

### Nested Layouts

Dashboard uses a nested layout:

```
RootLayout (theme, conditional header)
└── DashboardLayout (sidebar)
    └── Page Content
```

## Error Handling Patterns

### Form Submission

```typescript
const handleSubmit = async () => {
  setIsSubmitting(true);
  try {
    // API call
    await submitForm(data);
    router.push("/success");
  } catch (error) {
    // Handle error
    setError(error.message);
  } finally {
    setIsSubmitting(false);
  }
};
```

### Disabled Button State

Buttons show loading state during submission:

```typescript
<Button
  disabled={isSubmitting}
  sx={{
    "&.Mui-disabled": {
      bgcolor: "rgba(77, 138, 255, 0.6)",
      color: "rgba(255, 255, 255, 0.9)",
    },
  }}
>
  {isSubmitting ? "Submitting..." : "Submit"}
</Button>
```

## Performance Considerations

### Client vs Server Components

- **Server Components** (default): Static content, layouts
- **Client Components** (`"use client"`): Interactive forms, state

### Image Optimization

Use Next.js Image component:

```typescript
import Image from "next/image";

<Image
  src="/logo.png"
  alt="BVIRAL"
  width={80}
  height={32}
  priority // For above-fold images
/>
```

### Font Optimization

Fonts are loaded via `next/font`:

```typescript
import { Geist, Geist_Mono } from "next/font/google";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});
```
