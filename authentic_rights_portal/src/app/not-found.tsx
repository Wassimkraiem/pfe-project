import Link from "next/link";
import { Box, Typography, Button } from "@mui/material";

export default async function NotFound() {
  return (
    <Box
      sx={{
        minHeight: "100vh",
        bgcolor: "white",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        px: 2,
      }}
    >
      <Typography
        variant="h1"
        fontWeight="bold"
        sx={{ fontSize: { xs: "2.5rem", sm: "3rem" }, color: "#111827" }}
      >
        404
      </Typography>
      <Typography
        variant="h5"
        color="text.secondary"
        sx={{
          mt: 1,
          textAlign: "center",
          fontSize: { xs: "1rem", sm: "1.25rem" },
        }}
      >
        No onboarding session found with this link.
      </Typography>
      <Typography
        variant="body2"
        color="text.secondary"
        sx={{ mt: 1, textAlign: "center", maxWidth: "28rem" }}
      >
        The session may have expired or the link is invalid. Please start again
        from the beginning.
      </Typography>
      <Link href="/signup" style={{ textDecoration: "none" }}>
        <Button
          variant="contained"
          sx={{
            mt: 3,
            bgcolor: "#4D8AFF",
            "&:hover": { bgcolor: "#3D7AEF" },
            textTransform: "none",
            fontWeight: 600,
            borderRadius: 2,
            px: 3,
            py: 1.5,
          }}
        >
          Back to signup
        </Button>
      </Link>
    </Box>
  );
}
