import type { ThemeOptions } from "@mui/material/styles";

// BVIRAL Typography Configuration
// Using system font stack with Geist as primary
const fontFamily = [
  "var(--font-geist-sans)",
  "-apple-system",
  "BlinkMacSystemFont",
  '"Segoe UI"',
  "Roboto",
  '"Helvetica Neue"',
  "Arial",
  "sans-serif",
].join(", ");

export const typography: NonNullable<ThemeOptions["typography"]> = {
  fontFamily,

  // Heading styles
  h1: {
    fontWeight: 700,
    fontSize: "3rem", // 48px
    lineHeight: 1.2,
    letterSpacing: "-0.02em",
  },

  h2: {
    fontWeight: 700,
    fontSize: "2.25rem", // 36px
    lineHeight: 1.2,
    letterSpacing: "-0.01em",
  },

  h3: {
    fontWeight: 700,
    fontSize: "1.875rem", // 30px
    lineHeight: 1.3,
    letterSpacing: "-0.01em",
  },

  h4: {
    fontWeight: 700,
    fontSize: "1.5rem", // 24px
    lineHeight: 1.35,
  },

  h5: {
    fontWeight: 700,
    fontSize: "1.25rem", // 20px
    lineHeight: 1.4,
  },

  h6: {
    fontWeight: 700,
    fontSize: "1.125rem", // 18px
    lineHeight: 1.4,
  },

  // Body styles
  body1: {
    fontSize: "1rem", // 16px
    lineHeight: 1.6,
  },

  body2: {
    fontSize: "0.875rem", // 14px
    lineHeight: 1.5,
  },

  // Subtitle styles
  subtitle1: {
    fontSize: "1rem",
    fontWeight: 500,
    lineHeight: 1.5,
  },

  subtitle2: {
    fontSize: "0.875rem",
    fontWeight: 500,
    lineHeight: 1.5,
  },

  // Caption and overline
  caption: {
    fontSize: "0.75rem", // 12px
    lineHeight: 1.5,
  },

  overline: {
    fontSize: "0.75rem",
    fontWeight: 500,
    letterSpacing: "0.05em",
    textTransform: "uppercase",
    lineHeight: 1.5,
  },

  // Button typography
  button: {
    fontWeight: 600,
    fontSize: "0.875rem",
    textTransform: "none",
    lineHeight: 1.5,
  },
};
