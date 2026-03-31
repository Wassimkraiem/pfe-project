"use client";

import Link from "next/link";
import Image from "next/image";
import { UserButton } from "@clerk/nextjs";
import { useAuth } from "@clerk/nextjs";
import { Box, Button } from "@mui/material";


const loginButtonSx = {
  borderColor: "#4D8AFF",
  color: "#4D8AFF",
  "&:hover": {
    borderColor: "#3D7AEF",
    backgroundColor: "rgba(77, 138, 255, 0.08)",
  },
  textTransform: "none" as const,
  fontWeight: 600,
  borderRadius: "9999px",
  px: { xs: 1.5, sm: 2.5 },
  minWidth: 0,
  fontSize: { xs: "0.8125rem", sm: "0.875rem" },
};

export default function Header() {
  const { isSignedIn, isLoaded } = useAuth();

  return (
    <Box
      component="header"
      sx={{
        position: "sticky",
        top: 0,
        zIndex: 50,
        width: "100%",
        borderBottom: "1px solid rgba(0, 0, 0, 0.08)",
        bgcolor: "rgba(255, 255, 255, 0.95)",
        backdropFilter: "blur(8px)",
      }}
    >
      <Box
        sx={{
          maxWidth: "80rem",
          mx: "auto",
          display: "flex",
          height: 64,
          alignItems: "center",
          justifyContent: "space-between",
          px: { xs: 2, sm: 3, lg: 4 },
        }}
      >
        <Link href="/" style={{ display: "flex", alignItems: "center" }} aria-label="BVIRAL home">
          <Image
            src="/logo.png"
            alt="BVIRAL"
            width={100}
            height={40}
            style={{ height: 32, width: "auto" }}
            priority
          />
        </Link>

        {/* Desktop: login */}
        <Box
          sx={{
            display: { xs: "none", lg: "flex" },
            alignItems: "center",
            gap: 0.5,
          }}
        >
          {isLoaded &&
            (isSignedIn ? (
              <Box sx={{ display: "flex", alignItems: "center" }}>
                <UserButton afterSignOutUrl="/" />
              </Box>
            ) : (
              <Button
                component={Link}
                href="/signin"
                prefetch={false}
                variant="outlined"
                sx={loginButtonSx}
              >
                Log in
              </Button>
            ))}
        </Box>

        {/* Mobile: login/avatar */}
        <Box
          sx={{
            display: { xs: "flex", lg: "none" },
            alignItems: "center",
            gap: 0.5,
          }}
        >
          {isLoaded &&
            (isSignedIn ? (
              <Box sx={{ display: "flex", alignItems: "center" }}>
                <UserButton afterSignOutUrl="/" />
              </Box>
            ) : (
              <Button component={Link} href="/signin" prefetch={false} variant="outlined" sx={loginButtonSx}>
                Log in
              </Button>
            ))}
        </Box>
      </Box>

    </Box>
  );
}
