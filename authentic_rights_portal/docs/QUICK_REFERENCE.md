# Quick Reference Guide

A cheatsheet for common patterns used in the BVIRAL application.

## Common Imports

```tsx
// MUI Components
import {
  Box,
  Typography,
  Button,
  Card,
  CardContent,
  TextField,
  Chip,
  Tabs,
  Tab,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  IconButton,
  InputAdornment,
} from "@mui/material";

// Icons (Lucide React)
import {
  ArrowRight,
  ArrowLeft,
  Check,
  CheckCircle,
  CheckCircle2,
  X,
  Menu,
  Search,
  User,
  Users,
  Globe,
  ExternalLink,
  Calendar,
  CreditCard,
  FileText,
  HelpCircle,
  LayoutDashboard,
  Building2,
  DollarSign,
  TrendingUp,
  Clock,
  MoreHorizontal,
  Plus,
} from "lucide-react";

// Next.js
import Link from "next/link";
import Image from "next/image";
import { useRouter } from "next/navigation";
import { usePathname } from "next/navigation";
import { useSearchParams } from "next/navigation";
```

## Color Reference

```tsx
// Primary Blue
"#4D8AFF"              // Main
"#3D7AEF"              // Hover/Dark

// Dark/Secondary
"#111827"              // Main (text, dark buttons)
"#1f2937"              // Hover

// Text
"#111827"              // Primary
"#6b7280"              // Secondary (text.secondary)
"#9ca3af"              // Disabled/Icons

// Borders
"#e5e7eb"              // Light (cards)
"#d1d5db"              // Medium (inputs)
"#f3f4f6"              // Lightest (table rows)

// Backgrounds
"#ffffff"              // White
"#fafafa"              // Dashboard bg
"#f9fafb"              // Alternate bg
"#f3f4f6"              // Gray chips/tabs bg

// Status
"#ef4444"              // Error/Red
"#22c55e"              // Success/Green
"#f97316"              // Warning/Orange
```

## Button Patterns

```tsx
// Primary (Blue, Pill)
<Button
  variant="contained"
  sx={{
    bgcolor: "#4D8AFF",
    "&:hover": { bgcolor: "#3D7AEF" },
    textTransform: "none",
    fontWeight: 600,
    borderRadius: "9999px",
  }}
>
  Primary Action
</Button>

// Primary (Blue, Rounded)
<Button
  variant="contained"
  sx={{
    bgcolor: "#4D8AFF",
    "&:hover": { bgcolor: "#3D7AEF" },
    textTransform: "none",
    fontWeight: 600,
    borderRadius: 2,
  }}
>
  Submit
</Button>

// Dark (Secondary)
<Button
  variant="contained"
  sx={{
    bgcolor: "#111827",
    "&:hover": { bgcolor: "#1f2937" },
    textTransform: "none",
    fontWeight: 600,
    borderRadius: "9999px",
  }}
>
  Dark Action
</Button>

// Outlined
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

// With Icon
<Button
  variant="contained"
  endIcon={<ArrowRight style={{ width: 16, height: 16 }} />}
>
  Continue
</Button>

// As Link
<Button component={Link} href="/path">
  Go to Page
</Button>

// Loading/Disabled State
<Button
  disabled={isSubmitting}
  sx={{
    "&.Mui-disabled": {
      bgcolor: "rgba(77, 138, 255, 0.6)",
      color: "rgba(255, 255, 255, 0.9)",
    },
  }}
>
  {isSubmitting ? "Loading..." : "Submit"}
</Button>
```

## Card Patterns

```tsx
// Standard Card
<Card sx={{ borderRadius: 3, boxShadow: "none", border: "1px solid #e5e7eb" }}>
  <CardContent sx={{ p: 3 }}>
    <Typography variant="h6" fontWeight="bold">Title</Typography>
    <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
      Description
    </Typography>
  </CardContent>
</Card>

// Blue Highlight Card
<Box
  sx={{
    p: 4,
    borderRadius: 3,
    border: "1px solid #dbeafe",
    background: "linear-gradient(to right, #eff6ff, rgba(239, 246, 255, 0.3))",
  }}
>
  {/* Content */}
</Box>

// Green Highlight Card
<Box
  sx={{
    p: 4,
    borderRadius: 3,
    border: "1px solid #d1fae5",
    background: "linear-gradient(to right, #ecfdf5, rgba(236, 253, 245, 0.3))",
  }}
>
  {/* Content */}
</Box>
```

## Chip/Badge Patterns

```tsx
// Active / Premium (Dark)
<Chip label="Active" size="small" sx={{ bgcolor: "#111827", color: "white", fontWeight: 500 }} />

// Inactive / Error (Red)
<Chip label="Inactive" size="small" sx={{ bgcolor: "#ef4444", color: "white", fontWeight: 500 }} />

// Pending / Free / Basic (Gray)
<Chip label="Pending" size="small" sx={{ bgcolor: "#f3f4f6", color: "#4b5563", fontWeight: 500 }} />

// With Icon
<Chip
  icon={<Clock style={{ width: 12, height: 12 }} />}
  label="Pending"
  size="small"
  sx={{ bgcolor: "#f3f4f6", color: "#4b5563", "& .MuiChip-icon": { color: "#4b5563" } }}
/>
```

## Input Patterns

```tsx
// Standard Input
<TextField
  type="email"
  placeholder="Email address"
  value={value}
  onChange={(e) => setValue(e.target.value)}
  fullWidth
  sx={{
    "& .MuiOutlinedInput-root": {
      borderRadius: 2,
      height: 48,
      "&:hover fieldset": { borderColor: "#4D8AFF" },
      "&.Mui-focused fieldset": { borderColor: "#4D8AFF" },
    },
  }}
/>

// With Search Icon
<TextField
  placeholder="Search..."
  InputProps={{
    startAdornment: (
      <InputAdornment position="start">
        <Search style={{ width: 16, height: 16, color: "#9ca3af" }} />
      </InputAdornment>
    ),
  }}
/>

// Small Size
<TextField size="small" />
```

## Typography Patterns

```tsx
// Page Title
<Typography variant="h4" fontWeight="bold">Page Title</Typography>

// Section Title
<Typography variant="h6" fontWeight="bold">Section Title</Typography>

// Description
<Typography variant="body1" color="text.secondary">Description text</Typography>

// Small Text
<Typography variant="body2" color="text.secondary">Small text</Typography>

// Caption/Label
<Typography variant="caption" color="text.secondary" sx={{ textTransform: "uppercase", letterSpacing: "0.05em" }}>
  LABEL
</Typography>

// Responsive Text
<Typography sx={{ fontSize: { xs: "1.5rem", sm: "1.875rem", md: "2.25rem" } }}>
  Responsive Heading
</Typography>
```

## Layout Patterns

```tsx
// Page Container
<Box sx={{ minHeight: "100vh", bgcolor: "#fafafa" }}>
  <Box sx={{ px: { xs: 2, sm: 3, lg: 4 }, py: { xs: 4, sm: 6 } }}>
    {/* Content */}
  </Box>
</Box>

// Centered Content
<Box sx={{ maxWidth: "42rem", mx: "auto" }}>
  {/* Content */}
</Box>

// Flex Row (Responsive)
<Box sx={{ display: "flex", flexDirection: { xs: "column", sm: "row" }, gap: 2 }}>
  {/* Items */}
</Box>

// Grid (Responsive)
<Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", sm: "repeat(2, 1fr)", md: "repeat(3, 1fr)" }, gap: 3 }}>
  {/* Items */}
</Box>

// Space Between
<Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
  {/* Left */}
  {/* Right */}
</Box>
```

## Common Page Structure

```tsx
"use client";

import { useState } from "react";
import Link from "next/link";
import { Box, Typography, Button, Card, CardContent } from "@mui/material";
import { SomeIcon } from "lucide-react";

export default function MyPage() {
  const [state, setState] = useState("");

  return (
    <Box sx={{ minHeight: "100vh", bgcolor: "#fafafa" }}>
      <Box sx={{ px: { xs: 2, sm: 3, lg: 4 }, py: { xs: 4, sm: 6 } }}>
        {/* Header */}
        <Box>
          <Typography variant="h5" fontWeight="bold">
            Page Title
          </Typography>
          <Typography variant="body1" color="text.secondary" sx={{ mt: 0.5 }}>
            Page description
          </Typography>
        </Box>

        {/* Main Content Card */}
        <Card sx={{ mt: 4, borderRadius: 3, boxShadow: "none", border: "1px solid #e5e7eb" }}>
          <CardContent sx={{ p: 3 }}>
            {/* Card content */}
          </CardContent>
        </Card>
      </Box>
    </Box>
  );
}
```

## Icon Sizing

```tsx
// Small (buttons, badges)
<Icon style={{ width: 12, height: 12 }} />

// Default (inline text)
<Icon style={{ width: 16, height: 16 }} />

// Medium (standalone)
<Icon style={{ width: 20, height: 20 }} />

// Large (feature icons)
<Icon style={{ width: 24, height: 24 }} />

// With color
<Icon style={{ width: 20, height: 20, color: "#4D8AFF" }} />
<Icon style={{ width: 20, height: 20, color: "#9ca3af" }} />
```

## Form Submission Pattern

```tsx
const [isSubmitting, setIsSubmitting] = useState(false);
const router = useRouter();

const handleSubmit = async () => {
  setIsSubmitting(true);
  try {
    // API call here
    console.log("Submitting...");
    
    // Redirect on success
    router.push("/success-page");
  } catch (error) {
    console.error(error);
    // Handle error
  } finally {
    setIsSubmitting(false);
  }
};

<Button
  onClick={handleSubmit}
  disabled={isSubmitting}
  variant="contained"
  sx={{
    bgcolor: "#4D8AFF",
    "&:hover": { bgcolor: "#3D7AEF" },
    "&.Mui-disabled": { bgcolor: "rgba(77, 138, 255, 0.6)", color: "rgba(255, 255, 255, 0.9)" },
  }}
>
  {isSubmitting ? "Submitting..." : "Submit"}
</Button>
```

## Responsive Breakpoints

```tsx
// MUI Breakpoint Values
xs: 0      // Mobile (default)
sm: 640    // Tablet
md: 768    // Small desktop
lg: 1024   // Desktop
xl: 1280   // Large desktop

// Common Responsive Patterns
sx={{
  // Padding
  p: { xs: 2, sm: 3, lg: 4 },
  
  // Display
  display: { xs: "none", md: "block" },
  display: { xs: "block", md: "none" },
  
  // Flex direction
  flexDirection: { xs: "column", sm: "row" },
  
  // Font size
  fontSize: { xs: "1rem", sm: "1.25rem", md: "1.5rem" },
  
  // Grid columns
  gridTemplateColumns: { xs: "1fr", sm: "repeat(2, 1fr)", md: "repeat(3, 1fr)" },
  
  // Width
  width: { xs: "100%", sm: "auto" },
  maxWidth: { xs: "100%", sm: "28rem" },
}}
```

## Navigation

```tsx
// Link Navigation
import Link from "next/link";

<Link href="/path">Go to page</Link>
<Button component={Link} href="/path">Button Link</Button>

// Programmatic Navigation
import { useRouter } from "next/navigation";

const router = useRouter();
router.push("/path");
router.push(`/path?param=${value}`);

// Get Current Path
import { usePathname } from "next/navigation";

const pathname = usePathname();
const isActive = pathname === "/dashboard";

// Get URL Params
import { useSearchParams } from "next/navigation";

const searchParams = useSearchParams();
const email = searchParams.get("email");
```
