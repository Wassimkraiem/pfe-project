# Components Documentation

This document describes the reusable components in the BVIRAL application.

## Component Overview

| Component | Location | Purpose |
|-----------|----------|---------|
| `Header` | `src/components/Header.tsx` | Main navigation header |
| `ConditionalHeader` | `src/components/ConditionalHeader.tsx` | Conditionally renders header |
| `DashboardSidebar` | `src/components/DashboardSidebar.tsx` | Dashboard navigation |
| `StepIndicator` | `src/components/StepIndicator.tsx` | Multi-step progress |

---

## Header

Main navigation header with logo and menu links.

### Location
`src/components/Header.tsx`

### Features
- Logo (links to homepage)
- Navigation links (hidden on mobile)
- Hamburger menu for mobile (icon only, no drawer implemented)

### Usage
Automatically included via `ConditionalHeader` in root layout.

### Structure
```tsx
<Box component="header">
  <Box sx={{ maxWidth: "80rem", mx: "auto" }}>
    {/* Logo */}
    <Link href="/">
      <Image src="/logo.png" ... />
    </Link>
    
    {/* Desktop Navigation */}
    <Box sx={{ display: { xs: "none", md: "flex" } }}>
      {navItems.map(item => ...)}
    </Box>
    
    {/* Mobile Menu Icon */}
    <IconButton sx={{ display: { md: "none" } }}>
      <Menu />
    </IconButton>
  </Box>
</Box>
```

### Navigation Items
- Submit a Video
- Content Creators
- Brands and Publishers
- IPSHIELD™
- Resources

---

## ConditionalHeader

Wrapper that shows/hides the Header based on current route.

### Location
`src/components/ConditionalHeader.tsx`

### Purpose
Hides the main header on dashboard pages where a sidebar is used instead.

### Hidden Routes
```typescript
const hideHeaderPaths = ["/dashboard"];
```

### Usage
```tsx
// In layout.tsx
import ConditionalHeader from "@/components/ConditionalHeader";

<body>
  <ConditionalHeader />
  <main>{children}</main>
</body>
```

### Implementation
```tsx
"use client";

import { usePathname } from "next/navigation";
import Header from "./Header";

export default function ConditionalHeader() {
  const pathname = usePathname();
  const hideHeader = pathname.startsWith("/dashboard");
  
  if (hideHeader) return null;
  return <Header />;
}
```

---

## DashboardSidebar

Fixed sidebar navigation for dashboard pages.

### Location
`src/components/DashboardSidebar.tsx`

### Features
- Logo and user name display
- Navigation links with active state
- Sign out button
- Fixed position (desktop), responsive (mobile)

### Navigation Items
| Label | Path | Icon |
|-------|------|------|
| Dashboard | `/dashboard` | `LayoutDashboard` |
| Manage Subscription | `/dashboard/subscription` | `CreditCard` |
| Support & Help | `/dashboard/support` | `HelpCircle` |
| Become an Affiliate | `/dashboard/affiliate` | `Users` |

### Usage
Included automatically via dashboard layout:

```tsx
// src/app/dashboard/layout.tsx
import DashboardSidebar from "@/components/DashboardSidebar";

export default function DashboardLayout({ children }) {
  return (
    <Box sx={{ display: "flex", minHeight: "100vh" }}>
      <DashboardSidebar />
      <Box component="main" sx={{ flex: 1, ml: { lg: "224px" } }}>
        {children}
      </Box>
    </Box>
  );
}
```

### Active State
Active link determined by current pathname:

```tsx
const isActive = pathname === item.path;

<Button
  sx={{
    bgcolor: isActive ? "#f3f4f6" : "transparent",
    color: isActive ? "#111827" : "#6b7280",
    fontWeight: isActive ? 600 : 500,
  }}
>
```

### Styling
```tsx
// Sidebar container
<Box
  sx={{
    position: "fixed",
    top: 0,
    left: 0,
    height: "100vh",
    width: 224,           // 56 * 4 = 224px
    bgcolor: "white",
    borderRight: "1px solid #e5e7eb",
    display: { xs: "none", lg: "flex" },
    flexDirection: "column",
  }}
>
```

---

## StepIndicator

Multi-step progress indicator showing completed, current, and upcoming steps.

### Location
`src/components/StepIndicator.tsx`

### Props

| Prop | Type | Description |
|------|------|-------------|
| `steps` | `Step[]` | Array of step objects |
| `currentStep` | `number` | Current active step (1-indexed) |

### Step Object

```typescript
interface Step {
  number: number;  // Step number (1, 2, 3, ...)
  label: string;   // Step label ("Email", "Pages", etc.)
}
```

### Usage

```tsx
import StepIndicator from "@/components/StepIndicator";

const steps = [
  { number: 1, label: "Email" },
  { number: 2, label: "Pages" },
  { number: 3, label: "Checkout" },
  { number: 4, label: "Account" },
];

export default function SignupPage() {
  const currentStep = 2;
  
  return (
    <StepIndicator steps={steps} currentStep={currentStep} />
  );
}
```

### Visual States

| State | Circle Style | Label Color | Line Color |
|-------|--------------|-------------|------------|
| Completed | Blue fill, white checkmark | Blue | Blue |
| Current | Blue border, blue number | Blue | Gray |
| Upcoming | Gray border, gray number | Gray | Gray |

### Example Output

```
[✓]━━━━━[2]━━━━━(3)━━━━━(4)
Email    Pages   Checkout  Account
(blue)   (blue)  (gray)    (gray)
```

### Implementation Details

```tsx
// Determine step status
const isCompleted = step.number < currentStep;
const isCurrent = step.number === currentStep;
const isUpcoming = step.number > currentStep;

// Circle styles
const circleStyle = {
  width: 32,
  height: 32,
  borderRadius: "50%",
  border: `2px solid ${isCompleted || isCurrent ? "#4D8AFF" : "#d1d5db"}`,
  bgcolor: isCompleted ? "#4D8AFF" : "transparent",
  color: isCompleted ? "white" : isCurrent ? "#4D8AFF" : "#9ca3af",
};

// Line between steps
const lineStyle = {
  height: 2,
  bgcolor: isCompleted ? "#4D8AFF" : "#e5e7eb",
  flex: 1,
};
```

### Responsive Behavior

```tsx
// Container with horizontal scroll on mobile
<Box
  sx={{
    display: "flex",
    alignItems: "flex-start",
    justifyContent: "space-between",
    overflowX: "auto",
    px: { xs: 1, sm: 0 },
  }}
>
```

---

## Creating New Components

### Component Template

```tsx
"use client";  // Add if using hooks or browser APIs

import { Box, Typography, Button } from "@mui/material";
import { SomeIcon } from "lucide-react";

interface MyComponentProps {
  title: string;
  description?: string;
  onAction?: () => void;
}

export default function MyComponent({
  title,
  description,
  onAction,
}: MyComponentProps) {
  return (
    <Box
      sx={{
        p: 3,
        borderRadius: 3,
        border: "1px solid #e5e7eb",
      }}
    >
      <Typography variant="h6" fontWeight="bold">
        {title}
      </Typography>
      
      {description && (
        <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
          {description}
        </Typography>
      )}
      
      {onAction && (
        <Button
          onClick={onAction}
          variant="contained"
          sx={{
            mt: 2,
            bgcolor: "#4D8AFF",
            "&:hover": { bgcolor: "#3D7AEF" },
          }}
        >
          Take Action
        </Button>
      )}
    </Box>
  );
}
```

### Best Practices

1. **Use TypeScript interfaces** for props
2. **Add `"use client"`** only when needed (hooks, event handlers)
3. **Follow existing styling patterns** from theme
4. **Make components responsive** with `sx` breakpoints
5. **Use MUI components** (Box, Typography, Button) not raw HTML
6. **Import icons from Lucide React** with inline sizing

### File Location

Place new components in `src/components/`:

```
src/components/
├── Header.tsx
├── ConditionalHeader.tsx
├── DashboardSidebar.tsx
├── StepIndicator.tsx
└── MyNewComponent.tsx    ← Add here
```
