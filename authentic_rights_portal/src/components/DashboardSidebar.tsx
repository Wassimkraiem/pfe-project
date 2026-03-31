"use client";

import { usePathname } from "next/navigation";
import Link from "next/link";
import Image from "next/image";
import {
  LayoutGrid,
  CreditCard,
  HelpCircle,
  FileSpreadsheet,
  ClipboardList,
  LogOut,
  ListVideo,
  Upload,
} from "lucide-react";
import { Box, Typography, Button } from "@mui/material";
import { useClerk, useUser } from "@clerk/nextjs";
import type { LucideIcon } from "lucide-react";

type NavItem = {
  label: string;
  href: string;
  icon: LucideIcon;
  newTab?: boolean;
};

const navItems: NavItem[] = [
  {
    label: "Dashboard",
    href: "/dashboard",
    icon: LayoutGrid,
  },
  {
    label: "My Playlists",
    href: "/dashboard/playlists",
    icon: ListVideo,
  },
  {
    label: "Submit Video",
    href: "/dashboard/submit-video",
    icon: Upload,
  },
  {
    label: "Manage Subscription",
    href: "/dashboard/subscription",
    icon: CreditCard,
  },
  {
    label: "Support & Help",
    href: "/dashboard/support",
    icon: HelpCircle,
  },
];

const adminNavItems: NavItem[] = [
  {
    label: "Pending Quotes",
    href: "/dashboard/custom-quotes",
    icon: FileSpreadsheet,
  },
  {
    label: "Quotes Status",
    href: "/dashboard/quotes-status",
    icon: ClipboardList,
  },
];

export default function DashboardSidebar() {
  const pathname = usePathname();
  const { signOut } = useClerk();
  const { user } = useUser();
  const isAdmin = (() => {
    const metadata = user?.publicMetadata as Record<string, unknown> | undefined;
    return metadata?.role === "admin" || metadata?.isAdmin === true;
  })();
  const visibleNavItems: NavItem[] = isAdmin ? adminNavItems : navItems;

  return (
    <Box
      component="aside"
      sx={{
        position: "fixed",
        top: 0,
        left: 0,
        zIndex: 40,
        display: "flex",
        flexDirection: "column",
        height: "100vh",
        width: 224,
        borderRight: "1px solid #e5e7eb",
        bgcolor: "white",
      }}
    >
      {/* Logo */}
      <Box sx={{ p: 2 }}>
        <Link href="/dashboard" style={{ display: "block" }}>
          <Image
            src="/logo.png"
            alt="BVIRAL"
            width={80}
            height={32}
            style={{ height: 32, width: "auto" }}
          />
        </Link>
      </Box>

      {/* Navigation */}
      <Box component="nav" sx={{ flex: 1, p: 1.5 }}>
        <Box
          component="ul"
          sx={{
            display: "flex",
            flexDirection: "column",
            gap: 0.5,
            listStyle: "none",
            p: 0,
            m: 0,
          }}
        >
          {visibleNavItems.map((item) => {
            const isActive = pathname === item.href;
            return (
              <Box component="li" key={item.href}>
                <Link
                  href={item.href}
                  style={{ textDecoration: "none" }}
                  target={item.newTab ? "_blank" : undefined}
                  rel={item.newTab ? "noreferrer noopener" : undefined}
                >
                  <Box
                    sx={{
                      display: "flex",
                      alignItems: "center",
                      gap: 1.5,
                      px: 1.5,
                      py: 1.25,
                      borderRadius: 2,
                      fontSize: "0.875rem",
                      fontWeight: 500,
                      transition: "all 0.2s",
                      bgcolor: isActive ? "#f3f4f6" : "transparent",
                      color: isActive ? "#111827" : "#6b7280",
                      "&:hover": {
                        bgcolor: isActive ? "#f3f4f6" : "#f9fafb",
                        color: "#111827",
                      },
                    }}
                  >
                    <item.icon style={{ width: 20, height: 20 }} />
                    {item.label}
                  </Box>
                </Link>
              </Box>
            );
          })}
        </Box>
      </Box>

      {/* Sign Out */}
      <Box sx={{ borderTop: "1px solid #e5e7eb", p: 1.5 }}>
        <Button
          fullWidth
          startIcon={<LogOut style={{ width: 20, height: 20 }} />}
          onClick={() => signOut({ redirectUrl: "/signin" })}
          sx={{
            justifyContent: "flex-start",
            px: 1.5,
            py: 1.25,
            color: "#ef4444",
            textTransform: "none",
            fontWeight: 500,
            fontSize: "0.875rem",
            "&:hover": { bgcolor: "#fef2f2" },
          }}
        >
          Sign Out
        </Button>
      </Box>
    </Box>
  );
}
