# MUI Theme Guide

This guide explains how to use and extend the BVIRAL theme system.

## Theme Structure

```
src/theme/
├── index.ts          # Main theme export
├── palette.ts        # Color definitions
├── typography.ts     # Font & text styles
├── components.ts     # Component overrides
└── ThemeRegistry.tsx # Theme provider
```

## Color Palette

### Primary Colors

| Name | Hex | Usage |
|------|-----|-------|
| `primary.main` | `#4D8AFF` | Main blue - CTAs, links, accents |
| `primary.dark` | `#3D7AEF` | Hover states |
| `primary.light` | `#6B9FFF` | Light accents |

### Secondary Colors (Dark)

| Name | Hex | Usage |
|------|-----|-------|
| `secondary.main` | `#111827` | Dark buttons, headings |
| `secondary.dark` | `#1f2937` | Dark hover states |
| `secondary.light` | `#374151` | Lighter dark elements |

### Status Colors

| Name | Hex | Usage |
|------|-----|-------|
| `error.main` | `#ef4444` | Errors, destructive actions |
| `success.main` | `#10b981` | Success states |
| `warning.main` | `#f97316` | Warnings, growth indicators |

### Text Colors

| Name | Hex | Usage |
|------|-----|-------|
| `text.primary` | `#111827` | Headings, main text |
| `text.secondary` | `#6b7280` | Descriptions, muted text |
| `text.disabled` | `#9ca3af` | Disabled elements |

### Background Colors

| Name | Hex | Usage |
|------|-----|-------|
| `background.default` | `#ffffff` | Main background |
| `background.paper` | `#ffffff` | Card backgrounds |
| `background.subtle` | `#fafafa` | Dashboard background |
| `background.muted` | `#f9fafb` | Alternate background |

### Gray Scale

```typescript
grey: {
  50:  "#f9fafb",  // Lightest
  100: "#f3f4f6",  // Chip backgrounds
  200: "#e5e7eb",  // Borders
  300: "#d1d5db",  // Input borders
  400: "#9ca3af",  // Icons
  500: "#6b7280",  // Secondary text
  600: "#4b5563",  // Table headers
  700: "#374151",  // Darker text
  800: "#1f2937",  // Dark hover
  900: "#111827",  // Darkest
}
```

## Typography

### Font Family

```css
font-family: var(--font-geist-sans), -apple-system, BlinkMacSystemFont, 
             "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
```

### Heading Styles

| Variant | Size | Weight | Line Height |
|---------|------|--------|-------------|
| `h1` | 3rem (48px) | 700 | 1.2 |
| `h2` | 2.25rem (36px) | 700 | 1.2 |
| `h3` | 1.875rem (30px) | 700 | 1.3 |
| `h4` | 1.5rem (24px) | 700 | 1.35 |
| `h5` | 1.25rem (20px) | 700 | 1.4 |
| `h6` | 1.125rem (18px) | 700 | 1.4 |

### Body Styles

| Variant | Size | Line Height |
|---------|------|-------------|
| `body1` | 1rem (16px) | 1.6 |
| `body2` | 0.875rem (14px) | 1.5 |
| `caption` | 0.75rem (12px) | 1.5 |
| `overline` | 0.75rem (12px) | 1.5 (uppercase) |

### Usage

```tsx
import { Typography } from "@mui/material";

// Heading
<Typography variant="h4" fontWeight="bold">Title</Typography>

// Body text
<Typography variant="body1" color="text.secondary">
  Description text here
</Typography>

// Custom size
<Typography sx={{ fontSize: { xs: "1rem", sm: "1.25rem" } }}>
  Responsive text
</Typography>
```

## Button Styles

### Variants

#### Contained (Primary)

```tsx
<Button variant="contained" color="primary">
  Primary Action
</Button>

// Custom blue button
<Button
  variant="contained"
  sx={{
    bgcolor: "#4D8AFF",
    "&:hover": { bgcolor: "#3D7AEF" },
    textTransform: "none",
    fontWeight: 600,
    borderRadius: "9999px", // Pill shape
  }}
>
  Get Started
</Button>
```

#### Contained (Secondary/Dark)

```tsx
<Button variant="contained" color="secondary">
  Dark Button
</Button>

// Custom dark button
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
  Open Portal
</Button>
```

#### Outlined

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

### Disabled State

Disabled buttons have white text on a lighter blue background for readability:

```tsx
<Button
  disabled={isLoading}
  sx={{
    "&.Mui-disabled": {
      bgcolor: "rgba(77, 138, 255, 0.6)",
      color: "rgba(255, 255, 255, 0.9)",
    },
  }}
>
  {isLoading ? "Loading..." : "Submit"}
</Button>
```

### With Icons

```tsx
import { ArrowRight, ExternalLink } from "lucide-react";

<Button
  variant="contained"
  endIcon={<ArrowRight style={{ width: 16, height: 16 }} />}
>
  Continue
</Button>

<Button
  variant="contained"
  startIcon={<ExternalLink style={{ width: 16, height: 16 }} />}
>
  Open Link
</Button>
```

## Card Styles

### Standard Card

```tsx
import { Card, CardContent } from "@mui/material";

<Card
  sx={{
    borderRadius: 3,        // 12px
    boxShadow: "none",
    border: "1px solid #e5e7eb",
  }}
>
  <CardContent sx={{ p: 3 }}>
    {/* Content */}
  </CardContent>
</Card>
```

### Highlighted Card (Blue)

```tsx
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
```

### Highlighted Card (Green)

```tsx
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

## Chip/Badge Styles

### Status Chips

```tsx
import { Chip } from "@mui/material";

// Active (dark)
<Chip
  label="Active"
  size="small"
  sx={{
    bgcolor: "#111827",
    color: "white",
    fontWeight: 500,
    fontSize: "0.75rem",
  }}
/>

// Premium (dark - same as active)
<Chip
  label="Premium"
  size="small"
  sx={{
    bgcolor: "#111827",
    color: "white",
    fontWeight: 500,
    fontSize: "0.75rem",
  }}
/>

// Inactive (red)
<Chip
  label="Inactive"
  size="small"
  sx={{
    bgcolor: "#ef4444",
    color: "white",
    fontWeight: 500,
    fontSize: "0.75rem",
  }}
/>

// Pending / Free / Basic (gray)
<Chip
  label="Pending"
  size="small"
  sx={{
    bgcolor: "#f3f4f6",
    color: "#4b5563",
    fontWeight: 500,
    fontSize: "0.75rem",
  }}
/>

// Paid (gray)
<Chip
  label="Paid"
  size="small"
  sx={{
    bgcolor: "#f3f4f6",
    color: "#374151",
    fontWeight: 500,
    fontSize: "0.75rem",
  }}
/>
```

### Chips with Icons

```tsx
import { Clock, CheckCircle } from "lucide-react";

<Chip
  icon={<Clock style={{ width: 12, height: 12, color: "#4b5563" }} />}
  label="Pending"
  size="small"
  sx={{
    bgcolor: "#f3f4f6",
    color: "#4b5563",
  }}
/>
```

## TextField Styles

### Standard Input

```tsx
import { TextField } from "@mui/material";

<TextField
  placeholder="Enter text..."
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
```

### With Icon/Adornment

```tsx
import { InputAdornment } from "@mui/material";
import { Search } from "lucide-react";

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
```

## Table Styles

```tsx
import {
  Table, TableBody, TableCell, TableContainer,
  TableHead, TableRow
} from "@mui/material";

<TableContainer>
  <Table>
    <TableHead>
      <TableRow
        sx={{
          "& th": {
            borderColor: "#e5e7eb",
            fontWeight: 500,
            color: "#4b5563",
          },
        }}
      >
        <TableCell>Name</TableCell>
        <TableCell>Email</TableCell>
        <TableCell>Status</TableCell>
      </TableRow>
    </TableHead>
    <TableBody>
      <TableRow sx={{ "& td": { borderColor: "#f3f4f6" } }}>
        <TableCell sx={{ fontWeight: 500 }}>John Doe</TableCell>
        <TableCell sx={{ color: "#6b7280" }}>john@example.com</TableCell>
        <TableCell>
          <Chip label="Active" size="small" sx={{ bgcolor: "#111827", color: "white" }} />
        </TableCell>
      </TableRow>
    </TableBody>
  </Table>
</TableContainer>
```

## Tabs Styles

### Pill-Style Tabs

```tsx
import { Tabs, Tab } from "@mui/material";

<Tabs
  value={activeTab}
  onChange={(_, value) => setActiveTab(value)}
  sx={{
    bgcolor: "#f3f4f6",
    borderRadius: "9999px",
    p: 0.5,
    minHeight: "auto",
    "& .MuiTabs-indicator": { display: "none" },
    "& .MuiTab-root": {
      minHeight: "auto",
      py: 1.25,
      px: 3,
      borderRadius: "9999px",
      textTransform: "none",
      fontWeight: 500,
      fontSize: "0.875rem",
      color: "#6b7280",
      "&.Mui-selected": {
        bgcolor: "white",
        color: "#111827",
        border: "1px solid #d1d5db",
        boxShadow: "0 1px 2px 0 rgb(0 0 0 / 0.05)",
      },
    },
  }}
>
  <Tab value="overview" label="Overview" />
  <Tab value="users" label="Users" />
  <Tab value="quotes" label="Quotes" />
</Tabs>
```

## Spacing & Layout

### Common Spacing Values

```typescript
// MUI spacing unit = 8px
// p: 1 = 8px, p: 2 = 16px, p: 3 = 24px, p: 4 = 32px

// Page padding
px: { xs: 2, sm: 3, lg: 4 }  // 16px → 24px → 32px
py: { xs: 3, sm: 4 }         // 24px → 32px

// Card padding
p: 3                         // 24px

// Gap between elements
gap: 1.5                     // 12px
gap: 2                       // 16px
gap: 3                       // 24px
```

### Max-Width Containers

```typescript
// Full-width content area
maxWidth: "80rem"    // 1280px

// Form containers
maxWidth: "56rem"    // 896px
maxWidth: "42rem"    // 672px
maxWidth: "36rem"    // 576px
maxWidth: "28rem"    // 448px
```

### Responsive Flex/Grid

```tsx
// Responsive flex direction
<Box
  sx={{
    display: "flex",
    flexDirection: { xs: "column", sm: "row" },
    gap: 2,
  }}
>

// Responsive grid
<Box
  sx={{
    display: "grid",
    gridTemplateColumns: { xs: "1fr", sm: "repeat(2, 1fr)", md: "repeat(3, 1fr)" },
    gap: 3,
  }}
>
```

## Extending the Theme

### Adding New Colors

Edit `src/theme/palette.ts`:

```typescript
export const palette = {
  // ... existing colors
  
  // Add new color
  custom: {
    purple: "#8B5CF6",
    purpleDark: "#7C3AED",
  },
};
```

### Adding Component Overrides

Edit `src/theme/components.ts`:

```typescript
export const components = {
  // ... existing overrides
  
  // Add new component override
  MuiAlert: {
    styleOverrides: {
      root: {
        borderRadius: 8,
      },
      standardError: {
        backgroundColor: "#fef2f2",
        color: "#991b1b",
      },
    },
  },
};
```

### Using Theme in Components

```tsx
import { useTheme } from "@mui/material/styles";

function MyComponent() {
  const theme = useTheme();
  
  return (
    <Box
      sx={{
        color: theme.palette.primary.main,
        // Or use string reference
        bgcolor: "primary.light",
      }}
    />
  );
}
```
