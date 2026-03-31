"use client";

import { createTheme, ThemeOptions } from "@mui/material/styles";
import { palette } from "./palette";
import { typography } from "./typography";
import { components } from "./components";

// BVIRAL Theme Configuration
const themeOptions: ThemeOptions = {
  palette: {
    mode: "light",
    primary: palette.primary,
    secondary: palette.secondary,
    error: palette.error,
    success: palette.success,
    warning: palette.warning,
    text: palette.text,
    background: {
      default: palette.background.default,
      paper: palette.background.paper,
    },
    grey: palette.grey,
    divider: palette.divider,
    action: palette.action,
  },
  typography,
  components,
  shape: {
    borderRadius: 8,
  },
  spacing: 8,
  breakpoints: {
    values: {
      xs: 0,
      sm: 640,
      md: 768,
      lg: 1024,
      xl: 1280,
    },
  },
};

export const theme = createTheme(themeOptions);

// Re-export palette for custom components
export { palette };
export type { ThemeOptions };
