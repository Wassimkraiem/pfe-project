import { Components, Theme } from "@mui/material/styles";
import { palette } from "./palette";

// BVIRAL Component Overrides
export const components: Components<Theme> = {
  // Button styles
  MuiButton: {
    defaultProps: {
      disableElevation: true,
    },
    styleOverrides: {
      root: {
        textTransform: "none",
        fontWeight: 600,
        borderRadius: 8,
        padding: "10px 20px",
        "&.Mui-disabled": {
          color: "rgba(255, 255, 255, 0.8)",
        },
      },
      contained: {
        "&:hover": {
          boxShadow: "none",
        },
        "&.Mui-disabled": {
          backgroundColor: "rgba(77, 138, 255, 0.6)",
          color: "rgba(255, 255, 255, 0.9)",
        },
      },
      containedPrimary: {
        backgroundColor: palette.primary.main,
        "&:hover": {
          backgroundColor: palette.primary.dark,
        },
        "&.Mui-disabled": {
          backgroundColor: "rgba(77, 138, 255, 0.6)",
          color: "rgba(255, 255, 255, 0.9)",
        },
      },
      containedSecondary: {
        backgroundColor: palette.secondary.main,
        "&:hover": {
          backgroundColor: palette.secondary.dark,
        },
        "&.Mui-disabled": {
          backgroundColor: "rgba(17, 24, 39, 0.6)",
          color: "rgba(255, 255, 255, 0.9)",
        },
      },
      outlined: {
        borderColor: palette.border.main,
        color: palette.text.primary,
        "&:hover": {
          borderColor: palette.border.dark,
          backgroundColor: "transparent",
        },
      },
      outlinedPrimary: {
        borderColor: palette.primary.main,
        color: palette.primary.main,
        "&:hover": {
          borderColor: palette.primary.dark,
          backgroundColor: "rgba(77, 138, 255, 0.04)",
        },
      },
      text: {
        color: palette.text.primary,
        "&:hover": {
          backgroundColor: palette.action.hover,
        },
      },
      sizeSmall: {
        padding: "6px 16px",
        fontSize: "0.75rem",
      },
      sizeLarge: {
        padding: "14px 28px",
        fontSize: "1rem",
      },
    },
  },

  // Card styles
  MuiCard: {
    defaultProps: {
      elevation: 0,
    },
    styleOverrides: {
      root: {
        borderRadius: 12,
        border: `1px solid ${palette.border.light}`,
        boxShadow: "none",
      },
    },
  },

  MuiCardContent: {
    styleOverrides: {
      root: {
        padding: 24,
        "&:last-child": {
          paddingBottom: 24,
        },
      },
    },
  },

  // Chip styles
  MuiChip: {
    styleOverrides: {
      root: {
        fontWeight: 500,
        fontSize: "0.75rem",
        borderRadius: 6,
      },
      sizeSmall: {
        height: 24,
      },
      filled: {
        "&.MuiChip-colorDefault": {
          backgroundColor: palette.grey[100],
          color: palette.grey[600],
        },
        "&.MuiChip-colorPrimary": {
          backgroundColor: palette.primary.main,
          color: palette.primary.contrastText,
        },
        "&.MuiChip-colorSecondary": {
          backgroundColor: palette.secondary.main,
          color: palette.secondary.contrastText,
        },
        "&.MuiChip-colorSuccess": {
          backgroundColor: palette.success.main,
          color: palette.success.contrastText,
        },
        "&.MuiChip-colorError": {
          backgroundColor: palette.error.main,
          color: palette.error.contrastText,
        },
      },
      outlined: {
        borderColor: palette.border.main,
      },
    },
  },

  // TextField styles
  MuiTextField: {
    defaultProps: {
      variant: "outlined",
      size: "medium",
    },
    styleOverrides: {
      root: {
        "& .MuiOutlinedInput-root": {
          borderRadius: 8,
          "& fieldset": {
            borderColor: palette.border.light,
          },
          "&:hover fieldset": {
            borderColor: palette.primary.main,
          },
          "&.Mui-focused fieldset": {
            borderColor: palette.primary.main,
            borderWidth: 2,
          },
        },
      },
    },
  },

  MuiOutlinedInput: {
    styleOverrides: {
      root: {
        borderRadius: 8,
        "& fieldset": {
          borderColor: palette.border.light,
        },
        "&:hover fieldset": {
          borderColor: palette.primary.main,
        },
        "&.Mui-focused fieldset": {
          borderColor: palette.primary.main,
          borderWidth: 2,
        },
      },
      input: {
        padding: "12px 14px",
      },
    },
  },

  // Tabs styles
  MuiTabs: {
    styleOverrides: {
      root: {
        minHeight: "auto",
      },
      indicator: {
        display: "none",
      },
    },
  },

  MuiTab: {
    styleOverrides: {
      root: {
        minHeight: "auto",
        padding: "10px 24px",
        borderRadius: 9999,
        textTransform: "none",
        fontWeight: 500,
        fontSize: "0.875rem",
        color: palette.grey[500],
        "&.Mui-selected": {
          backgroundColor: "#ffffff",
          color: palette.text.primary,
          border: `1px solid ${palette.border.main}`,
          boxShadow: "0 1px 2px 0 rgb(0 0 0 / 0.05)",
        },
      },
    },
  },

  // Table styles
  MuiTable: {
    styleOverrides: {
      root: {
        borderCollapse: "separate",
        borderSpacing: 0,
      },
    },
  },

  MuiTableHead: {
    styleOverrides: {
      root: {
        "& .MuiTableCell-head": {
          fontWeight: 500,
          color: palette.grey[600],
          borderColor: palette.border.light,
          backgroundColor: "transparent",
        },
      },
    },
  },

  MuiTableRow: {
    styleOverrides: {
      root: {
        "&:hover": {
          backgroundColor: palette.grey[50],
        },
      },
    },
  },

  MuiTableCell: {
    styleOverrides: {
      root: {
        borderColor: palette.grey[100],
        padding: "16px",
      },
      head: {
        fontWeight: 500,
        color: palette.grey[600],
      },
    },
  },

  // IconButton styles
  MuiIconButton: {
    styleOverrides: {
      root: {
        color: palette.text.secondary,
        "&:hover": {
          backgroundColor: palette.action.hover,
        },
      },
    },
  },

  // Paper styles
  MuiPaper: {
    defaultProps: {
      elevation: 0,
    },
    styleOverrides: {
      root: {
        backgroundImage: "none",
      },
      rounded: {
        borderRadius: 12,
      },
    },
  },

  // Divider styles
  MuiDivider: {
    styleOverrides: {
      root: {
        borderColor: palette.border.light,
      },
    },
  },

  // Link styles
  MuiLink: {
    styleOverrides: {
      root: {
        color: palette.primary.main,
        textDecoration: "none",
        "&:hover": {
          textDecoration: "underline",
        },
      },
    },
  },

  // Typography defaults
  MuiTypography: {
    styleOverrides: {
      gutterBottom: {
        marginBottom: "0.5em",
      },
    },
  },

  // Container styles
  MuiContainer: {
    styleOverrides: {
      root: {
        paddingLeft: 16,
        paddingRight: 16,
        "@media (min-width: 600px)": {
          paddingLeft: 24,
          paddingRight: 24,
        },
      },
    },
  },

  // InputAdornment styles
  MuiInputAdornment: {
    styleOverrides: {
      root: {
        color: palette.text.secondary,
      },
    },
  },
};
