"use client";

import { useEffect, useMemo, useState } from "react";
import { useAuth, useUser } from "@clerk/nextjs";
import {
  Alert,
  Box,
  Chip,
  CircularProgress,
  Collapse,
  FormControl,
  IconButton,
  InputLabel,
  MenuItem,
  Paper,
  Select,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
  Typography,
} from "@mui/material";
import { ChevronDown, ChevronUp } from "lucide-react";
import { getCustomQuotesStatus, CustomQuoteStatusItem } from "@/lib/api";
import { getApiToken } from "@/lib/auth";

function formatDate(value: string | undefined): string {
  if (!value) return "-";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  return parsed.toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function readString(source: Record<string, unknown>, keys: string[]): string {
  for (const key of keys) {
    const value = source[key];
    if (typeof value === "string" && value.trim()) return value.trim();
    if (typeof value === "number") return String(value);
  }
  return "";
}

type StatusRow = {
  email: string;
  priceId: string;
  paid: boolean;
  createdAt: string;
  channels: string[];
  accountCreated: boolean;
};

function StatusRowWithChannels({ row }: { row: StatusRow }) {
  const [expanded, setExpanded] = useState(false);
  const hasChannels = row.channels.length > 0;
  const hasMultiple = row.channels.length > 1;

  return (
    <>
      <TableRow sx={{ "&:last-child td": { border: 0 } }}>
        <TableCell sx={{ fontWeight: 500, fontSize: "0.875rem", py: 1.5 }}>
          {row.email}
        </TableCell>
        <TableCell sx={{ fontSize: "0.8125rem", fontFamily: "monospace", py: 1.5 }}>
          {row.priceId}
        </TableCell>
        <TableCell sx={{ py: 1.5 }}>
          <Chip
            label={row.paid ? "Paid" : "Unpaid"}
            size="small"
            sx={{
              fontWeight: 600,
              fontSize: "0.75rem",
              textTransform: "capitalize",
              bgcolor: row.paid ? "rgba(34, 197, 94, 0.12)" : "rgba(239, 68, 68, 0.08)",
              color: row.paid ? "#15803d" : "#dc2626",
              border: "1px solid",
              borderColor: row.paid ? "rgba(34, 197, 94, 0.3)" : "rgba(239, 68, 68, 0.2)",
            }}
          />
        </TableCell>
        <TableCell sx={{ py: 1.5 }}>
          {row.accountCreated ? (
            <Chip
              label="Account Created"
              size="small"
              sx={{
                fontWeight: 600,
                fontSize: "0.75rem",
                bgcolor: "rgba(34, 197, 94, 0.12)",
                color: "#15803d",
                border: "1px solid",
                borderColor: "rgba(34, 197, 94, 0.3)",
              }}
            />
          ) : (
            <Chip
              label="Account Not Created"
              size="small"
              sx={{
                fontWeight: 600,
                fontSize: "0.75rem",
                bgcolor: "rgba(107, 114, 128, 0.1)",
                color: "#6b7280",
                border: "1px solid",
                borderColor: "rgba(107, 114, 128, 0.2)",
              }}
            />
          )}
        </TableCell>
        <TableCell sx={{ py: 1.5 }}>
          {hasChannels ? (
            <Box sx={{ display: "flex", alignItems: "center", gap: 0.5, minWidth: 0 }}>
              {hasMultiple ? (
                <>
                  <IconButton
                    size="small"
                    onClick={() => setExpanded(!expanded)}
                    aria-label={expanded ? "Collapse" : "Expand channels"}
                    sx={{ p: 0.25, flexShrink: 0 }}
                  >
                    {expanded ? <ChevronUp style={{ width: 18, height: 18 }} /> : <ChevronDown style={{ width: 18, height: 18 }} />}
                  </IconButton>
                  <Typography variant="body2" color="text.secondary" sx={{ flexShrink: 0 }}>
                    {row.channels.length} channel{row.channels.length !== 1 ? "s" : ""}
                  </Typography>
                </>
              ) : (
                <Box
                  component="a"
                  href={/^https?:\/\//i.test(row.channels[0]) ? row.channels[0] : `https://${row.channels[0]}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  sx={{
                    color: "#4D8AFF",
                    wordBreak: "break-all",
                    textDecoration: "underline",
                    fontSize: "0.75rem",
                    "&:hover": { color: "#3D7AEF" },
                  }}
                >
                  {row.channels[0]}
                </Box>
              )}
            </Box>
          ) : (
            <Typography variant="caption" color="text.secondary">-</Typography>
          )}
        </TableCell>
        <TableCell sx={{ fontSize: "0.8125rem", color: "text.secondary", py: 1.5, whiteSpace: "nowrap" }}>
          {row.createdAt}
        </TableCell>
      </TableRow>
      {hasChannels && hasMultiple && (
        <TableRow>
          <TableCell colSpan={6} sx={{ py: 0, borderBottom: expanded ? undefined : "none", verticalAlign: "top" }}>
            <Collapse in={expanded} timeout="auto" unmountOnExit>
              <Box sx={{ py: 1.5, pl: 2, pr: 2, bgcolor: "rgba(0,0,0,0.02)" }}>
                <Typography variant="caption" fontWeight={600} color="text.secondary" sx={{ mb: 1, display: "block" }}>
                  All channels
                </Typography>
                <Box
                  component="ul"
                  sx={{ m: 0, pl: 2.5, display: "flex", flexDirection: "column", gap: 0.5 }}
                >
                  {row.channels.map((url, ci) => {
                    const href = /^https?:\/\//i.test(url) ? url : `https://${url}`;
                    return (
                      <Box
                        key={ci}
                        component="li"
                        sx={{ listStyle: "disc" }}
                      >
                        <Box
                          component="a"
                          href={href}
                          target="_blank"
                          rel="noopener noreferrer"
                          sx={{
                            color: "#4D8AFF",
                            wordBreak: "break-all",
                            textDecoration: "underline",
                            fontSize: "0.8125rem",
                            "&:hover": { color: "#3D7AEF" },
                          }}
                        >
                          {url}
                        </Box>
                      </Box>
                    );
                  })}
                </Box>
              </Box>
            </Collapse>
          </TableCell>
        </TableRow>
      )}
    </>
  );
}

function toStatusRows(items: CustomQuoteStatusItem[]): StatusRow[] {
  return items.map((item) => {
    const obj = item as Record<string, unknown>;
    const channels = Array.isArray(item.channels)
      ? item.channels.filter(Boolean)
      : Array.isArray(item.custom_quote_triggers)
        ? item.custom_quote_triggers.map((t) => t.channel_url ?? "").filter(Boolean)
        : [];
    const paid = item._paid === true || item.payment_received === true;
    const currentStep = readString(obj, ["current_step"]).toLowerCase();
    const accountCreated = currentStep === "complete" || currentStep === "done" || currentStep === "completed";
    return {
      email: readString(obj, ["email", "user_email"]) || "-",
      priceId: readString(obj, ["price_id"]) || "-",
      paid,
      createdAt: formatDate(item.created_at ?? readString(obj, ["created_at", "submitted_at"])),
      channels,
      accountCreated,
    };
  });
}

export default function QuotesStatusPage() {
  const { isLoaded, isSignedIn, getToken } = useAuth();
  const { user } = useUser();
  const [items, setItems] = useState<CustomQuoteStatusItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [emailFilter, setEmailFilter] = useState("");
  const [paymentFilter, setPaymentFilter] = useState<"all" | "paid" | "unpaid">("all");

  const isAdmin = useMemo(() => {
    if (!user) return false;
    const metadata = user.publicMetadata as Record<string, unknown> | undefined;
    return metadata?.role === "admin" || metadata?.isAdmin === true;
  }, [user]);

  const rows = useMemo(() => toStatusRows(items), [items]);

  const filteredRows = useMemo(() => {
    return rows.filter((row) => {
      const matchesEmail =
        !emailFilter.trim() ||
        row.email.toLowerCase().includes(emailFilter.trim().toLowerCase());
      const matchesPayment =
        paymentFilter === "all" ||
        (paymentFilter === "paid" && row.paid) ||
        (paymentFilter === "unpaid" && !row.paid);
      return matchesEmail && matchesPayment;
    });
  }, [rows, emailFilter, paymentFilter]);

  useEffect(() => {
    if (!isLoaded || !isSignedIn || !isAdmin) return;
    let active = true;
    (async () => {
      setLoading(true);
      setError(null);
      try {
        const token = await getApiToken(getToken);
        if (!token) throw new Error("Missing auth token.");
        const data = await getCustomQuotesStatus(token);
        if (active) setItems(data);
      } catch (err) {
        if (active) setError(err instanceof Error ? err.message : "Failed to load quote statuses.");
      } finally {
        if (active) setLoading(false);
      }
    })();
    return () => { active = false; };
  }, [isLoaded, isSignedIn, isAdmin, getToken]);

  if (!isLoaded) {
    return (
      <Box sx={{ py: 8, display: "flex", justifyContent: "center" }}>
        <CircularProgress size={30} />
      </Box>
    );
  }

  if (!isSignedIn) {
    return (
      <Box sx={{ py: 8, textAlign: "center" }}>
        <Typography color="text.secondary">Please sign in to continue.</Typography>
      </Box>
    );
  }

  if (!isAdmin) {
    return (
      <Box sx={{ minHeight: "100vh", bgcolor: "#fafafa" }}>
        <Box sx={{ px: { xs: 2, sm: 3, lg: 4 }, py: { xs: 4, sm: 6 } }}>
          <Alert severity="error">Admins only: you do not have access to this page.</Alert>
        </Box>
      </Box>
    );
  }

  return (
    <Box sx={{ minHeight: "100vh", bgcolor: "#fafafa" }}>
      <Box sx={{ px: { xs: 2, sm: 3, lg: 4 }, py: { xs: 4, sm: 6 } }}>
        <Typography variant="h5" fontWeight="bold">
          Custom Quotes Status
        </Typography>
        <Typography variant="body1" color="text.secondary" sx={{ mt: 0.5 }}>
          Track submitted custom quotes and their payment status.
        </Typography>

        {error && (
          <Alert severity="error" sx={{ mt: 3 }}>
            {error}
          </Alert>
        )}

        <Box
          sx={{
            mt: 3,
            display: "flex",
            flexDirection: { xs: "column", sm: "row" },
            gap: 2,
          }}
        >
          <TextField
            label="Filter by email"
            placeholder="Search email..."
            value={emailFilter}
            onChange={(e) => setEmailFilter(e.target.value)}
            size="small"
            sx={{
              minWidth: { sm: 240 },
              "& .MuiOutlinedInput-root": { borderRadius: 2 },
            }}
          />
          <FormControl size="small" sx={{ minWidth: 160 }}>
            <InputLabel>Payment status</InputLabel>
            <Select
              value={paymentFilter}
              label="Payment status"
              onChange={(e) => setPaymentFilter(e.target.value as "all" | "paid" | "unpaid")}
              sx={{ borderRadius: 2 }}
            >
              <MenuItem value="all">All</MenuItem>
              <MenuItem value="paid">Paid</MenuItem>
              <MenuItem value="unpaid">Unpaid</MenuItem>
            </Select>
          </FormControl>
        </Box>

        <TableContainer
          component={Paper}
          sx={{
            mt: 2,
            borderRadius: 3,
            boxShadow: "none",
            border: "1px solid #e5e7eb",
          }}
        >
          <Table>
            <TableHead>
              <TableRow sx={{ bgcolor: "rgba(0,0,0,0.02)" }}>
                <TableCell sx={{ fontWeight: 700, fontSize: "0.8125rem", color: "text.secondary", py: 1.5 }}>
                  Email
                </TableCell>
                <TableCell sx={{ fontWeight: 700, fontSize: "0.8125rem", color: "text.secondary", py: 1.5 }}>
                  Price ID
                </TableCell>
                <TableCell sx={{ fontWeight: 700, fontSize: "0.8125rem", color: "text.secondary", py: 1.5 }}>
                  Status
                </TableCell>
                <TableCell sx={{ fontWeight: 700, fontSize: "0.8125rem", color: "text.secondary", py: 1.5 }}>
                  Account
                </TableCell>
                <TableCell sx={{ fontWeight: 700, fontSize: "0.8125rem", color: "text.secondary", py: 1.5, minWidth: 160 }}>
                  Channels
                </TableCell>
                <TableCell sx={{ fontWeight: 700, fontSize: "0.8125rem", color: "text.secondary", py: 1.5 }}>
                  Date
                </TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {loading ? (
                <TableRow>
                  <TableCell colSpan={6} sx={{ textAlign: "center", py: 6 }}>
                    <CircularProgress size={28} sx={{ color: "#4D8AFF" }} />
                    <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                      Loading...
                    </Typography>
                  </TableCell>
                </TableRow>
              ) : filteredRows.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={6} sx={{ textAlign: "center", py: 6 }}>
                    <Typography variant="body2" color="text.secondary">
                      {rows.length === 0
                        ? "No custom quote submissions found."
                        : "No results match your filters."}
                    </Typography>
                  </TableCell>
                </TableRow>
              ) : (
                filteredRows.map((row, i) => (
                  <StatusRowWithChannels key={`${row.email}-${i}`} row={row} />
                ))
              )}
            </TableBody>
          </Table>
        </TableContainer>
      </Box>
    </Box>
  );
}
