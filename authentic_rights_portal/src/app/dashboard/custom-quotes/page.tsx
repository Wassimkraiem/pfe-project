"use client";

import { useEffect, useMemo, useState } from "react";
import { useAuth, useUser } from "@clerk/nextjs";
import {
  Alert,
  Box,
  Button,
  CircularProgress,
  TextField,
  Typography,
  Chip,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Collapse,
  IconButton,
} from "@mui/material";
import { ChevronDown, ChevronUp, Check } from "lucide-react";
import { createCustomQuoteOnboardingSessionPrice, getPendingCustomQuotes } from "@/lib/api";
import { getApiToken } from "@/lib/auth";

type CustomQuoteTrigger = {
  channel_url: string;
  message: string;
};

type QuoteRow = {
  id: string;
  email: string;
  createdAt: string;
  customQuoteTriggers: CustomQuoteTrigger[];
  priceId: string | null;
};

function readString(source: Record<string, unknown>, keys: string[]): string {
  for (const key of keys) {
    const value = source[key];
    if (typeof value === "string" && value.trim()) return value.trim();
    if (typeof value === "number") return String(value);
  }
  return "";
}

function readCustomQuoteTriggers(source: Record<string, unknown>): CustomQuoteTrigger[] {
  const triggers = source.custom_quote_triggers;
  if (!Array.isArray(triggers)) return [];
  return triggers
    .map((t) => {
      if (!t || typeof t !== "object") return null;
      const obj = t as Record<string, unknown>;
      const channelUrl = typeof obj.channel_url === "string" ? obj.channel_url.trim() : "";
      const message = typeof obj.message === "string" ? obj.message.trim() : "";
      if (!channelUrl && !message) return null;
      return { channel_url: channelUrl || "-", message: message || "-" };
    })
    .filter((t): t is CustomQuoteTrigger => t !== null);
}

function formatDate(value: string): string {
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

function toQuoteRows(items: unknown[]): QuoteRow[] {
  return items.map((item, index) => {
    const obj = item && typeof item === "object" ? (item as Record<string, unknown>) : {};
    const id = readString(obj, ["id", "quote_id", "custom_quote_id"]) || `row-${index + 1}`;
    const email = readString(obj, ["email", "user_email"]);
    const createdAt = readString(obj, ["created_at", "submitted_at", "createdAt"]);
    const customQuoteTriggers = readCustomQuoteTriggers(obj);
    const priceId = readString(obj, ["price_id"]) || null;

    return {
      id,
      email: email || "-",
      createdAt: formatDate(createdAt),
      customQuoteTriggers,
      priceId,
    };
  });
}

function InlinePriceEditor({
  email,
  existingPriceId,
  getToken,
  onSuccess,
}: {
  email: string;
  existingPriceId: string | null;
  getToken: () => Promise<string | null>;
  onSuccess: () => void;
}) {
  const [priceId, setPriceId] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  if (existingPriceId) {
    return (
      <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
        <Chip
          icon={<Check style={{ width: 14, height: 14 }} />}
          label={existingPriceId}
          size="small"
          color="success"
          variant="outlined"
          sx={{ fontWeight: 600, fontSize: "0.75rem" }}
        />
      </Box>
    );
  }

  if (success) {
    return (
      <Chip
        icon={<Check style={{ width: 14, height: 14 }} />}
        label="Price set"
        size="small"
        color="success"
        variant="outlined"
        sx={{ fontWeight: 600 }}
      />
    );
  }

  const handleSubmit = async () => {
    if (!priceId.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const token = await getApiToken(getToken);
      if (!token) throw new Error("Missing auth token.");
      await createCustomQuoteOnboardingSessionPrice(token, email, priceId.trim());
      setSuccess(true);
      setPriceId("");
      onSuccess();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box sx={{ display: "flex", alignItems: "center", gap: 1, minWidth: 240 }}>
      <TextField
        placeholder="price_..."
        value={priceId}
        onChange={(e) => { setPriceId(e.target.value); setError(null); }}
        size="small"
        error={!!error}
        helperText={error}
        onKeyDown={(e) => e.key === "Enter" && handleSubmit()}
        sx={{
          flex: 1,
          "& .MuiOutlinedInput-root": { borderRadius: 1.5, height: 36 },
          "& .MuiInputBase-input": { fontSize: "0.8125rem" },
        }}
      />
      <Button
        onClick={handleSubmit}
        disabled={loading || !priceId.trim()}
        variant="contained"
        size="small"
        sx={{
          height: 36,
          minWidth: 0,
          px: 2,
          bgcolor: "#4D8AFF",
          "&:hover": { bgcolor: "#3D7AEF" },
          textTransform: "none",
          fontWeight: 600,
          borderRadius: 1.5,
          fontSize: "0.8125rem",
          flexShrink: 0,
        }}
      >
        {loading ? <CircularProgress size={16} color="inherit" /> : "Set"}
      </Button>
    </Box>
  );
}

function ExpandableRow({
  quote,
  getToken,
  onPriceSet,
}: {
  quote: QuoteRow;
  getToken: () => Promise<string | null>;
  onPriceSet: () => void;
}) {
  const [open, setOpen] = useState(true);
  const hasTriggers = quote.customQuoteTriggers.length > 0;

  return (
    <>
      <TableRow sx={{ "&:last-child td, &:last-child th": { border: 0 } }}>
        <TableCell sx={{ py: 1.5 }}>
          {hasTriggers && (
            <IconButton size="small" onClick={() => setOpen(!open)}>
              {open ? <ChevronUp style={{ width: 16, height: 16 }} /> : <ChevronDown style={{ width: 16, height: 16 }} />}
            </IconButton>
          )}
        </TableCell>
        <TableCell sx={{ fontWeight: 500, fontSize: "0.875rem", py: 1.5 }}>
          {quote.email}
        </TableCell>
        <TableCell sx={{ fontSize: "0.8125rem", color: "text.secondary", py: 1.5 }}>
          {quote.createdAt}
        </TableCell>
        <TableCell sx={{ py: 1.5 }}>
          <InlinePriceEditor
            email={quote.email}
            existingPriceId={quote.priceId}
            getToken={getToken}
            onSuccess={onPriceSet}
          />
        </TableCell>
      </TableRow>
      {hasTriggers && (
        <TableRow>
          <TableCell colSpan={4} sx={{ py: 0, borderBottom: open ? undefined : "none" }}>
            <Collapse in={open} timeout="auto" unmountOnExit>
              <Box sx={{ py: 1.5, pl: 6 }}>
                <Typography variant="caption" fontWeight={600} color="text.secondary" sx={{ mb: 1, display: "block" }}>
                  Custom quote triggers
                </Typography>
                {quote.customQuoteTriggers.map((trigger, i) => {
                  const href = /^https?:\/\//i.test(trigger.channel_url)
                    ? trigger.channel_url
                    : `https://${trigger.channel_url}`;
                  return (
                  <Box
                    key={i}
                    sx={{
                      display: "flex",
                      gap: 2,
                      py: 0.5,
                      fontSize: "0.8125rem",
                    }}
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
                        "&:hover": { color: "#3D7AEF" },
                        fontSize: "inherit",
                      }}
                    >
                      {trigger.channel_url}
                    </Box>
                    <Typography variant="body2" color="text.secondary">
                      {trigger.message}
                    </Typography>
                  </Box>
                );
                })}
              </Box>
            </Collapse>
          </TableCell>
        </TableRow>
      )}
    </>
  );
}

export default function CustomQuotesAdminPage() {
  const { isLoaded, isSignedIn, getToken } = useAuth();
  const { user } = useUser();

  const [pendingQuotes, setPendingQuotes] = useState<unknown[]>([]);
  const [loadingQuotes, setLoadingQuotes] = useState(false);
  const [quotesError, setQuotesError] = useState<string | null>(null);

  const isAdmin = useMemo(() => {
    if (!user) return false;
    const metadata = user.publicMetadata as Record<string, unknown> | undefined;
    const role = metadata?.role;
    const isAdminFlag = metadata?.isAdmin;
    return role === "admin" || isAdminFlag === true;
  }, [user]);

  const quoteRows = useMemo(() => toQuoteRows(pendingQuotes), [pendingQuotes]);

  const loadQuotes = async () => {
    setLoadingQuotes(true);
    setQuotesError(null);
    try {
      const token = await getApiToken(getToken);
      if (!token) throw new Error("Missing auth token. Please sign in again.");
      const list = await getPendingCustomQuotes(token);
      setPendingQuotes(list);
    } catch (err) {
      setQuotesError(err instanceof Error ? err.message : "Failed to load pending custom quotes.");
    } finally {
      setLoadingQuotes(false);
    }
  };

  useEffect(() => {
    if (!isLoaded || !isSignedIn || !isAdmin) return;
    loadQuotes();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isAdmin, isLoaded, isSignedIn]);

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
          Pending Custom Quotes
        </Typography>
        <Typography variant="body1" color="text.secondary" sx={{ mt: 0.5 }}>
          Review submitted custom quote requests. Add a price ID to each quote to let the user proceed to checkout.
        </Typography>

        {quotesError && (
          <Alert severity="error" sx={{ mt: 3 }}>
            {quotesError}
          </Alert>
        )}

        <TableContainer
          component={Paper}
          sx={{
            mt: 3,
            borderRadius: 3,
            boxShadow: "none",
            border: "1px solid #e5e7eb",
          }}
        >
          <Table>
            <TableHead>
              <TableRow sx={{ bgcolor: "rgba(0,0,0,0.02)" }}>
                <TableCell sx={{ width: 48, py: 1.5 }} />
                <TableCell sx={{ fontWeight: 700, fontSize: "0.8125rem", color: "text.secondary", py: 1.5 }}>
                  Email
                </TableCell>
                <TableCell sx={{ fontWeight: 700, fontSize: "0.8125rem", color: "text.secondary", py: 1.5 }}>
                  Submitted
                </TableCell>
                <TableCell sx={{ fontWeight: 700, fontSize: "0.8125rem", color: "text.secondary", py: 1.5, minWidth: 280 }}>
                  Price ID
                </TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {loadingQuotes ? (
                <TableRow>
                  <TableCell colSpan={4} sx={{ textAlign: "center", py: 6 }}>
                    <CircularProgress size={28} sx={{ color: "#4D8AFF" }} />
                    <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                      Loading quotes...
                    </Typography>
                  </TableCell>
                </TableRow>
              ) : quoteRows.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={4} sx={{ textAlign: "center", py: 6 }}>
                    <Typography variant="body2" color="text.secondary">
                      No pending custom quotes found.
                    </Typography>
                  </TableCell>
                </TableRow>
              ) : (
                quoteRows.map((quote) => (
                  <ExpandableRow
                    key={quote.id}
                    quote={quote}
                    getToken={getToken}
                    onPriceSet={loadQuotes}
                  />
                ))
              )}
            </TableBody>
          </Table>
        </TableContainer>
      </Box>
    </Box>
  );
}
