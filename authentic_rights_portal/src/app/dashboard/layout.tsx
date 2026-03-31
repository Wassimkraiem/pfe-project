"use client";

import { useEffect } from "react";
import { usePathname, useRouter } from "next/navigation";
import { UserButton, useAuth, useUser } from "@clerk/nextjs";
import DashboardSidebar from "@/components/DashboardSidebar";
import { Box, CircularProgress, Typography } from "@mui/material";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const { isLoaded, isSignedIn } = useAuth();
  const { user } = useUser();
  const router = useRouter();
  const pathname = usePathname();
  const isAdmin = (() => {
    const metadata = user?.publicMetadata as Record<string, unknown> | undefined;
    return metadata?.role === "admin" || metadata?.isAdmin === true;
  })();

  const adminPaths = ["/dashboard/custom-quotes", "/dashboard/quotes-status"];
  useEffect(() => {
    if (!isLoaded || !isSignedIn || !isAdmin) return;
    if (!adminPaths.includes(pathname)) {
      router.replace("/dashboard/custom-quotes");
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isAdmin, isLoaded, isSignedIn, pathname, router]);

  // Show loader until auth state is known; prevent flashing dashboard content when logged out
  if (!isLoaded) {
    return (
      <Box
        sx={{
          minHeight: "100vh",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          bgcolor: "rgba(249, 250, 251, 0.5)",
          gap: 2,
        }}
      >
        <CircularProgress size={40} sx={{ color: "#4D8AFF" }} />
        <Typography variant="body2" color="text.secondary">
          Loading…
        </Typography>
      </Box>
    );
  }

  // Redirecting to sign-in; show same loader so user doesn't see protected UI
  if (!isSignedIn) {
    return (
      <Box
        sx={{
          minHeight: "100vh",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          bgcolor: "rgba(249, 250, 251, 0.5)",
          gap: 2,
        }}
      >
        <CircularProgress size={40} sx={{ color: "#4D8AFF" }} />
        <Typography variant="body2" color="text.secondary">
          Redirecting to sign in…
        </Typography>
      </Box>
    );
  }

  if (isAdmin && !adminPaths.includes(pathname)) {
    return (
      <Box
        sx={{
          minHeight: "100vh",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          bgcolor: "rgba(249, 250, 251, 0.5)",
          gap: 2,
        }}
      >
        <CircularProgress size={40} sx={{ color: "#4D8AFF" }} />
        <Typography variant="body2" color="text.secondary">
          Redirecting…
        </Typography>
      </Box>
    );
  }

  return (
    <Box sx={{ minHeight: "100vh", bgcolor: "rgba(249, 250, 251, 0.5)" }}>
      {/* Sidebar - hidden on mobile, visible on lg+ */}
      <Box sx={{ display: { xs: "none", lg: "block" } }}>
        <DashboardSidebar />
      </Box>

      {/* Main Content - with left margin on lg+ for sidebar */}
      <Box component="main" sx={{ ml: { lg: "224px" } }}>
        <Box
          component="header"
          sx={{
            position: "sticky",
            top: 0,
            zIndex: 30,
            height: 56,
            display: "flex",
            alignItems: "center",
            justifyContent: "flex-end",
            px: { xs: 2, sm: 3, lg: 4 },
            bgcolor: "rgba(249, 250, 251, 0.85)",
            backdropFilter: "blur(8px)",
            borderBottom: "1px solid rgba(0,0,0,0.06)",
          }}
        >
          <UserButton
            afterSignOutUrl="/signin"
            appearance={{
              elements: {
                rootBox: { zIndex: 100 },
                card: { zIndex: 100 },
                userButtonPopoverCard: { zIndex: 100 },
              },
            }}
          />
        </Box>
        <Box sx={{ px: { xs: 2, sm: 3, lg: 4 }, pt: { xs: 1.5, sm: 2 }, pb: { xs: 3, sm: 4 } }}>{children}</Box>
      </Box>
    </Box>
  );
}
