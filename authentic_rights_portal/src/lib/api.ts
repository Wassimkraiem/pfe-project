export const BASE_URL =
  typeof process !== "undefined"
    ? process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"
    : "http://localhost:8000";

/** Path for Lemon Squeezy success redirect after payment (user clicks Continue). Use: /signup?session_id=<SESSION_ID> */
export const SIGNUP_SUCCESS_PATH = "/signup";

export type OnboardingSessionData = {
  id: number | null;
  uuid?: string | null;
  email: string;
  current_step: string | null;
  payment_received: boolean;
  price_id?: string | number | null;
  custom_quote_submitted?: boolean;
  session_details: Record<string, unknown> | null;
  pages?: { channels?: unknown[] } | null;
  channels?: string[];
  created_at: string | null;
  updated_at: string | null;
};

export type GetSessionByEmailResponse = {
  status_code: number;
  message: string;
  data: OnboardingSessionData | null;
};

export type GetSessionByUuidResponse = {
  status_code: number;
  message: string;
  data: OnboardingSessionData | null;
};

export function getOnboardingSessionPriceId(
  session: OnboardingSessionData | null | undefined
): string | null {
  const direct = session?.price_id;
  if (direct !== null && direct !== undefined) {
    const asString = String(direct).trim();
    if (asString) return asString;
  }
  const details = session?.session_details as { price_id?: string | number | null } | null;
  const nested = details?.price_id;
  if (nested !== null && nested !== undefined) {
    const asString = String(nested).trim();
    if (asString) return asString;
  }
  return null;
}

export function getOnboardingSessionChannelsCount(
  session: OnboardingSessionData | null | undefined
): number | null {
  const pages = (session?.session_details as { pages?: { channels?: unknown[] } } | null)?.pages ?? session?.pages;
  const channels = pages?.channels;
  if (!Array.isArray(channels)) return null;
  return channels.length;
}

export function getOnboardingSessionChannelUrls(
  session: OnboardingSessionData | null | undefined
): string[] {
  const pages = (session?.session_details as { pages?: { channels?: unknown[] } } | null)?.pages ?? session?.pages;
  const channels = pages?.channels;
  if (!Array.isArray(channels)) return [];
  return channels
    .map((item) => {
      if (typeof item === "string") return item.trim();
      if (item && typeof item === "object" && "url" in item) {
        const maybeUrl = (item as { url?: unknown }).url;
        return typeof maybeUrl === "string" ? maybeUrl.trim() : "";
      }
      return "";
    })
    .filter(Boolean);
}

/**
 * Get onboarding session by UUID.
 * GET /onboarding_sessions/{session_uuid}
 * Used by the frontend to validate the account step after payment (current_step === "account", payment_received === true).
 * Returns session data even on 404 if the response contains completion info (for "already completed" messaging).
 */
export async function getOnboardingSessionByUuid(
  sessionUuid: string
): Promise<GetSessionByUuidResponse> {
  const res = await fetch(
    `${BASE_URL}/onboarding_sessions/${encodeURIComponent(sessionUuid)}`
  );
  const json = (await res.json()) as GetSessionByUuidResponse;
  if (!res.ok) {
    if (res.status === 404) {
      const step = json.data?.current_step;
      const isCompleted = step === "complete" || step === "completed" || step === "done";
      if (json.data && isCompleted) {
        return { ...json, status_code: 200 };
      }
      throw new Error("No session exists with the provided UUID");
    }
    throw new Error(json.message ?? `Request failed: ${res.status}`);
  }
  return json;
}

/**
 * Get onboarding session by email.
 * POST /onboarding_sessions/get-session-by-email
 * Returns session if found; on success (2xx) proceed to step 2.
 * Pass signal to cancel when switching steps (avoids unused in-flight requests).
 */
export async function getOnboardingSessionByEmail(
  email: string,
  signal?: AbortSignal
): Promise<GetSessionByEmailResponse> {
  const request = async (path: string) => {
    const res = await fetch(`${BASE_URL}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email }),
      signal,
    });
    const raw = await res.text();
    let json: (GetSessionByEmailResponse & { error_message?: string }) | null = null;
    try {
      json = raw ? (JSON.parse(raw) as GetSessionByEmailResponse & { error_message?: string }) : null;
    } catch {
      json = null;
    }
    return { res, raw, json };
  };

  const primary = await request("/onboarding_sessions/get-session-by-email");
  if (primary.res.ok && primary.json) {
    return primary.json;
  }

  const shouldRetry =
    primary.res.status === 404 ||
    primary.res.status === 405 ||
    primary.res.status === 422;
  if (shouldRetry) {
    const fallback = await request("/onboarding_sessions/get_session_by_email");
    if (fallback.res.ok && fallback.json) {
      return fallback.json;
    }
    const msg =
      fallback.json?.error_message ??
      fallback.json?.message ??
      (fallback.raw ? fallback.raw : undefined) ??
      `Request failed: ${fallback.res.status}`;
    throw new Error(msg);
  }

  const msg =
    primary.json?.error_message ??
    primary.json?.message ??
    (primary.raw ? primary.raw : undefined) ??
    `Request failed: ${primary.res.status}`;
  throw new Error(msg);
}

/** Per-channel payload returned by channels/add (e.g. requires_custom_quote for 2M+ or manual review). */
export type ChannelAddItem = {
  url?: string;
  requires_custom_quote?: boolean;
};

/** Session-level flag returned by channels/add or get-session (custom quote required for 2M+ or manual review). */
export type AddChannelsResponse = {
  status_code?: number;
  message?: string;
  error_code?: string;
  error_message?: string;
  error_details?: { msg?: string; input?: string }[];
  /** Session-level: when true, one or more channels require custom quote. */
  requires_custom_quote?: boolean;
  data?: {
    channels?: ChannelAddItem[];
    requires_custom_quote?: boolean;
    /** When present, custom quote UI is shown if requires_custom_quote and this array has at least one item. */
    custom_quote_triggers?: { channel_url?: string; flag?: string }[];
  };
};

/**
 * Extract user-friendly error message from API validation errors.
 */
function extractValidationErrorMessage(json: AddChannelsResponse): string | null {
  if (json.error_details && Array.isArray(json.error_details) && json.error_details.length > 0) {
    const detail = json.error_details[0];
    if (detail.msg) {
      let msg = detail.msg;
      if (msg.startsWith("Value error, ")) {
        msg = msg.replace("Value error, ", "");
      }
      return msg;
    }
  }
  return null;
}

/**
 * Add channel URLs to an onboarding session (creates session if it doesn't exist).
 * POST /onboarding_sessions/channels/add
 * Throws with backend error_message on 409 (duplicate_channel_url) or other errors.
 */
export async function addChannelsToSession(
  email: string,
  channels: string[]
): Promise<AddChannelsResponse> {
  const res = await fetch(`${BASE_URL}/onboarding_sessions/channels/add`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, channels }),
  });
  const json = (await res.json()) as AddChannelsResponse;
  if (!res.ok) {
    const validationMsg = extractValidationErrorMessage(json);
    const msg =
      validationMsg ??
      (json.error_message !== "validation_error" ? json.error_message : null) ??
      json.message ??
      (res.status === 400 ? "Invalid URL. Please check and try again." : `Request failed: ${res.status}`);
    throw new Error(msg);
  }
  return json;
}

export type CreateCheckoutResponse = {
  status_code?: number;
  message?: string;
  data?: {
    checkout_url?: string;
    client_secret?: string;
    channels_count?: number;
    payment_flow_type?: string;
    plan?: string;
  };
};

/**
 * Create LemonSqueezy checkout link for an onboarding session.
 * POST /onboarding_sessions/checkout
 * Prerequisites: session exists for email, in PAGES step, with at least one channel.
 * Sends signature (digital signature captured before checkout) and plan (MONTHLY | YEARLY).
 */
export async function createCheckout(
  email: string,
  plan: "monthly" | "yearly",
  payment_flow_type: "subscription" | "custom_quote" = "subscription",
  signature: string,
  service_agreement_signed_at?: string | null
): Promise<CreateCheckoutResponse> {
  const planValue = plan === "yearly" ? "YEARLY" : "MONTHLY";
  const res = await fetch(`${BASE_URL}/onboarding_sessions/checkout`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      email,
      plan: planValue,
      payment_flow_type,
      signature: signature.trim(),
      service_agreement_signed_at: service_agreement_signed_at ?? null,
    }),
  });
  const json = (await res.json()) as CreateCheckoutResponse;
  if (!res.ok) {
    throw new Error(json.message ?? `Request failed: ${res.status}`);
  }
  return json;
}


// Add this to your api.ts file
export type RemoveChannelResponse = {
  status_code: number;
  message: string;
  data: OnboardingSessionData;
};

/**
 * Remove a single channel URL from an onboarding session.
 * POST /onboarding_sessions/channels/remove
 * Prerequisites:
 * - Session must exist for the provided email
 * - Session must be in PAGES step
 * - The channel URL must exist in the session
 */
export async function removeChannelFromSession(
  email: string,
  channelUrl: string
): Promise<RemoveChannelResponse> {
  const res = await fetch(`${BASE_URL}/onboarding_sessions/channels/remove`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ 
      email, 
      channel: channelUrl 
    }),
  });
  
  const json = (await res.json()) as RemoveChannelResponse;
  
  if (!res.ok) {
    // Handle specific error cases
    if (res.status === 404) {
      throw new Error("No session found for this email or channel URL not found.");
    }
    if (res.status === 400) {
      throw new Error("Session is not in PAGES step. Please refresh and try again.");
    }
    throw new Error(json.message ?? `Request failed: ${res.status}`);
  }
  
  return json;
}

export type PaymentResponse = {
  status_code?: number;
  message?: string;
  data?: {
    payment?: {
      status?: string;
      amount?: number;
      currency?: string;
      plan_type?: string;
    };
    subscription?: {
      id?: string;
      status?: string;
      next_billing_date?: string | null;
      cancel_at_period_end?: boolean;
    };
    renews_at?: string | null;
    next_billing_date?: string | null;
    current_period_end?: string | number | null;
    customer_portal_url?: string | null;
    renewal_failed?: boolean;
    renewal_grace_ends_at?: string | null;
    canto_access_suspended?: boolean;
  };
};

export type PaymentPriceData = {
  price?: number;
  plan?: "monthly" | "yearly";
};

export type PaymentPriceResponse = {
  status_code?: number;
  message?: string;
  data?: PaymentPriceData | null;
};

export async function getPaymentPrice(priceId: string): Promise<PaymentPriceResponse> {
  const res = await fetch(`${BASE_URL}/payments/prices/${encodeURIComponent(priceId)}`);
  const json = (await res.json()) as PaymentPriceResponse;
  if (!res.ok) {
    const msg = json.message ?? `Request failed: ${res.status}`;
    throw new Error(msg);
  }
  return json;
}

export async function getPaymentsMe(token: string): Promise<PaymentResponse> {
  const res = await fetch(`${BASE_URL}/payments/me`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  const json = (await res.json()) as PaymentResponse;
  if (!res.ok) {
    const msg = json.message ?? `Request failed: ${res.status}`;
    throw new Error(msg);
  }
  return json;
}

export type ChannelsResponse =
  | unknown[]
  | { data?: unknown }
  | { data?: { channels?: unknown } };

export async function getChannels(token: string): Promise<ChannelsResponse> {
  const res = await fetch(`${BASE_URL}/channels`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  const json = (await res.json()) as ChannelsResponse;
  if (!res.ok) {
    throw new Error(`Request failed: ${res.status}`);
  }
  return json;
}

export function getChannelUrlsFromResponse(response: ChannelsResponse): string[] {
  const data = Array.isArray(response)
    ? response
    : Array.isArray((response as { data?: unknown }).data)
      ? ((response as { data?: unknown }).data as unknown[])
      : Array.isArray((response as { data?: { channels?: unknown } }).data?.channels)
        ? ((response as { data?: { channels?: unknown } }).data?.channels as unknown[])
        : [];

  return data
    .map((item) => {
      if (typeof item === "string") return item.trim();
      if (!item || typeof item !== "object") return "";
      const channel = item as {
        url?: unknown;
        channel_url?: unknown;
        handle?: unknown;
        name?: unknown;
      };
      if (typeof channel.url === "string" && channel.url.trim()) return channel.url.trim();
      if (typeof channel.channel_url === "string" && channel.channel_url.trim()) return channel.channel_url.trim();
      if (typeof channel.handle === "string" && channel.handle.trim()) return channel.handle.trim();
      if (typeof channel.name === "string" && channel.name.trim()) return channel.name.trim();
      return "";
    })
    .filter(Boolean);
}

export type SubmitCustomQuoteResponse = {
  status_code: number;
  message: string;
  data?: unknown;
};

export type PendingCustomQuotesResponse = {
  status_code?: number;
  message?: string;
  data?: unknown;
  error_message?: string;
};

export type SetCustomQuotePriceResponse = {
  status_code?: number;
  message?: string;
  data?: unknown;
  error_message?: string;
};

/**
 * Create a custom quote from onboarding session (email only; channels fetched from session).
 * POST /custom-quotes/create
 */
export async function submitCustomQuoteRequest(
  email: string
): Promise<SubmitCustomQuoteResponse> {
  const res = await fetch(`${BASE_URL}/onboarding_sessions/create-custom-quote`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email: email.trim() }),
  });
  const json = (await res.json()) as SubmitCustomQuoteResponse & {
    error_message?: string;
    detail?: unknown;
  };
  if (!res.ok) {
    const msg =
      json.error_message ??
      json.message ??
      (Array.isArray(json.detail)
        ? json.detail.map((d: { msg?: string }) => d.msg).filter(Boolean).join(" ")
        : undefined) ??
      `Request failed: ${res.status}`;
    throw new Error(msg);
  }
  return json;
}

function readMessageFromUnknown(payload: unknown): string | null {
  if (!payload || typeof payload !== "object") return null;
  const obj = payload as { message?: unknown; error_message?: unknown };
  if (typeof obj.error_message === "string" && obj.error_message.trim()) {
    return obj.error_message;
  }
  if (typeof obj.message === "string" && obj.message.trim()) {
    return obj.message;
  }
  return null;
}

function readArrayFromUnknown(payload: unknown): unknown[] {
  if (Array.isArray(payload)) return payload;
  if (!payload || typeof payload !== "object") return [];
  const obj = payload as {
    data?: unknown;
    quotes?: unknown;
    custom_quotes?: unknown;
    items?: unknown;
  };
  if (Array.isArray(obj.data)) return obj.data;
  if (Array.isArray(obj.quotes)) return obj.quotes;
  if (Array.isArray(obj.custom_quotes)) return obj.custom_quotes;
  if (Array.isArray(obj.items)) return obj.items;
  return [];
}

export async function getPendingCustomQuotes(token: string): Promise<unknown[]> {
  const res = await fetch(`${BASE_URL}/onboarding_sessions/custom-quotes/pending`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
  const json = (await res.json()) as PendingCustomQuotesResponse;
  if (!res.ok) {
    const msg = readMessageFromUnknown(json) ?? `Request failed: ${res.status}`;
    throw new Error(msg);
  }
  return readArrayFromUnknown(json.data ?? json);
}

export type CustomQuoteStatusItem = {
  id?: number;
  uuid?: string;
  email?: string;
  price_id?: string;
  current_step?: string;
  payment_received?: boolean;
  requires_custom_quote?: boolean;
  custom_quote_submitted?: boolean;
  created_at?: string;
  updated_at?: string;
  channels?: string[];
  custom_quote_triggers?: { channel_url?: string; flag?: string; message?: string }[];
  session_details?: Record<string, unknown>;
  _paid: boolean;
  [key: string]: unknown;
};

export type CustomQuoteStatusResponse = {
  status_code?: number;
  message?: string;
  data?: {
    pending_payment?: unknown[];
    paid?: unknown[];
  } | unknown;
  error_message?: string;
};

export async function getCustomQuotesStatus(token: string): Promise<CustomQuoteStatusItem[]> {
  const res = await fetch(`${BASE_URL}/onboarding_sessions/custom-quotes/status`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
  const json = (await res.json()) as CustomQuoteStatusResponse;
  if (!res.ok) {
    const msg = readMessageFromUnknown(json) ?? `Request failed: ${res.status}`;
    throw new Error(msg);
  }
  const data = json.data;
  if (data && typeof data === "object" && !Array.isArray(data)) {
    const obj = data as { pending_payment?: unknown[]; paid?: unknown[] };
    const pendingRaw = Array.isArray(obj.pending_payment) ? obj.pending_payment : [];
    const paidRaw = Array.isArray(obj.paid) ? obj.paid : [];
    const tag = (items: unknown[], paid: boolean): CustomQuoteStatusItem[] =>
      items.map((item) => ({ ...(item as Record<string, unknown>), _paid: paid }) as CustomQuoteStatusItem);
    return [...tag(pendingRaw, false), ...tag(paidRaw, true)];
  }
  return readArrayFromUnknown(data ?? json).map(
    (item) => ({ ...(item as Record<string, unknown>), _paid: false }) as CustomQuoteStatusItem
  );
}

export async function createCustomQuoteOnboardingSessionPrice(
  token: string,
  email: string,
  priceId: string
): Promise<SetCustomQuotePriceResponse> {
  const res = await fetch(`${BASE_URL}/onboarding_sessions/custom-quote/price`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({
      email: email.trim(),
      price_id: priceId.trim(),
    }),
  });
  const json = (await res.json()) as SetCustomQuotePriceResponse;
  if (!res.ok) {
    const msg = readMessageFromUnknown(json) ?? `Request failed: ${res.status}`;
    throw new Error(msg);
  }
  return json;
}

/** Request body for completing onboarding (account step). */
export type CompleteAccountRequestBody = {
  first_name: string;
  last_name: string;
  account_type: "individual" | "business";
  company_name: string | null;
  password: string;
  confirm_password: string;
};

export type CompleteAccountResponse = {
  status_code: number;
  message: string;
  data?: {
    message: string;
    user_id: number;
    channels_created: number;
    payment_id: number;
  };
};

/**
 * Complete onboarding session (account step).
 * POST /onboarding_sessions/{session_uuid}/account
 * Prerequisites: session in ACCOUNT step, payment received, at least one channel.
 * Creates Clerk user, channel records, payment record; marks session completed.
 */
// ---------------------------------------------------------------------------
// Conversation API (chat persistence)
// ---------------------------------------------------------------------------

export type ConversationMessage = {
  id: number;
  role: "user" | "assistant";
  content: string;
  payload?: Record<string, unknown> | null;
  created_at: string;
};

export type ConversationSummary = {
  id: number;
  title: string | null;
  created_at: string;
  updated_at: string | null;
};

export type ConversationDetail = ConversationSummary & {
  messages: ConversationMessage[];
};

type ArEnvelope<T> = {
  status_code: number;
  message: string;
  data: T;
};

export async function getConversations(
  token: string,
): Promise<ConversationSummary[]> {
  const res = await fetch(`${BASE_URL}/conversations`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  const json = (await res.json()) as ArEnvelope<ConversationSummary[]>;
  if (!res.ok) throw new Error(json.message ?? `Request failed: ${res.status}`);
  return json.data;
}

export async function getConversation(
  token: string,
  conversationId: number,
): Promise<ConversationDetail> {
  const res = await fetch(`${BASE_URL}/conversations/${conversationId}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  const json = (await res.json()) as ArEnvelope<ConversationDetail>;
  if (!res.ok) throw new Error(json.message ?? `Request failed: ${res.status}`);
  return json.data;
}

export async function createConversation(
  token: string,
  payload: {
    title?: string;
    user_message: string;
    assistant_message: string;
    assistant_payload?: Record<string, unknown>;
  },
): Promise<ConversationSummary> {
  const res = await fetch(`${BASE_URL}/conversations`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });
  const json = (await res.json()) as ArEnvelope<ConversationSummary>;
  if (!res.ok) throw new Error(json.message ?? `Request failed: ${res.status}`);
  return json.data;
}

export async function addConversationMessages(
  token: string,
  conversationId: number,
  payload: {
    user_message: string;
    assistant_message: string;
    assistant_payload?: Record<string, unknown>;
  },
): Promise<ConversationDetail> {
  const res = await fetch(
    `${BASE_URL}/conversations/${conversationId}/messages`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify(payload),
    },
  );
  const json = (await res.json()) as ArEnvelope<ConversationDetail>;
  if (!res.ok) throw new Error(json.message ?? `Request failed: ${res.status}`);
  return json.data;
}

export async function deleteConversation(
  token: string,
  conversationId: number,
): Promise<void> {
  const res = await fetch(`${BASE_URL}/conversations/${conversationId}`, {
    method: "DELETE",
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) {
    const json = (await res.json()) as ArEnvelope<unknown>;
    throw new Error(json.message ?? `Request failed: ${res.status}`);
  }
}

// ---------------------------------------------------------------------------
// Playlists API
// ---------------------------------------------------------------------------

export const VIDEOS_API_URL =
  typeof process !== "undefined"
    ? process.env.NEXT_PUBLIC_VIDEOS_API_URL ?? "http://localhost:5000"
    : "http://localhost:5000";

export const VIDEOS_API_KEY =
  typeof process !== "undefined"
    ? process.env.NEXT_PUBLIC_VIDEOS_API_KEY ?? "key1"
    : "key1";

export type PlaylistVideo = {
  id: number;
  video_id: string;
  position: number;
  created_at: string;
};

export type PlaylistSummary = {
  id: number;
  title: string;
  description: string | null;
  created_at: string;
  updated_at: string | null;
  video_count: number;
};

export type PlaylistDetail = PlaylistSummary & {
  videos: PlaylistVideo[];
};

export async function getPlaylists(token: string): Promise<PlaylistSummary[]> {
  const res = await fetch(`${BASE_URL}/playlists`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  const json = (await res.json()) as ArEnvelope<PlaylistSummary[]>;
  if (!res.ok) throw new Error(json.message ?? `Request failed: ${res.status}`);
  return json.data;
}

export async function getPlaylist(
  token: string,
  playlistId: number,
): Promise<PlaylistDetail> {
  const res = await fetch(`${BASE_URL}/playlists/${playlistId}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  const json = (await res.json()) as ArEnvelope<PlaylistDetail>;
  if (!res.ok) throw new Error(json.message ?? `Request failed: ${res.status}`);
  return json.data;
}

export async function createPlaylist(
  token: string,
  payload: { title: string; description?: string; video_ids?: string[] },
): Promise<PlaylistSummary> {
  const res = await fetch(`${BASE_URL}/playlists`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });
  const json = (await res.json()) as ArEnvelope<PlaylistSummary>;
  if (!res.ok) throw new Error(json.message ?? `Request failed: ${res.status}`);
  return json.data;
}

export async function updatePlaylist(
  token: string,
  playlistId: number,
  payload: { title?: string; description?: string },
): Promise<PlaylistSummary> {
  const res = await fetch(`${BASE_URL}/playlists/${playlistId}`, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });
  const json = (await res.json()) as ArEnvelope<PlaylistSummary>;
  if (!res.ok) throw new Error(json.message ?? `Request failed: ${res.status}`);
  return json.data;
}

export async function deletePlaylist(
  token: string,
  playlistId: number,
): Promise<void> {
  const res = await fetch(`${BASE_URL}/playlists/${playlistId}`, {
    method: "DELETE",
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) {
    const json = (await res.json()) as ArEnvelope<unknown>;
    throw new Error(json.message ?? `Request failed: ${res.status}`);
  }
}

export async function addVideosToPlaylist(
  token: string,
  playlistId: number,
  videoIds: string[],
): Promise<PlaylistDetail> {
  const res = await fetch(`${BASE_URL}/playlists/${playlistId}/videos`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ video_ids: videoIds }),
  });
  const json = (await res.json()) as ArEnvelope<PlaylistDetail>;
  if (!res.ok) throw new Error(json.message ?? `Request failed: ${res.status}`);
  return json.data;
}

export async function removeVideoFromPlaylist(
  token: string,
  playlistId: number,
  videoId: string,
): Promise<void> {
  const res = await fetch(
    `${BASE_URL}/playlists/${playlistId}/videos/${encodeURIComponent(videoId)}`,
    {
      method: "DELETE",
      headers: { Authorization: `Bearer ${token}` },
    },
  );
  if (!res.ok) {
    const json = (await res.json()) as ArEnvelope<unknown>;
    throw new Error(json.message ?? `Request failed: ${res.status}`);
  }
}

// ---------------------------------------------------------------------------
// Video Submissions API
// ---------------------------------------------------------------------------

export type VideoSubmission = {
  id: number;
  title: string;
  description: string | null;
  video_url: string;
  tags: string[] | null;
  category: string | null;
  status: "pending" | "approved" | "rejected";
  admin_notes: string | null;
  created_at: string;
  updated_at: string | null;
};

export async function submitVideo(
  token: string,
  payload: {
    title: string;
    description?: string;
    video_url: string;
    tags?: string[];
    category?: string;
  },
): Promise<VideoSubmission> {
  const res = await fetch(`${BASE_URL}/video-submissions`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });
  const json = (await res.json()) as ArEnvelope<VideoSubmission>;
  if (!res.ok) throw new Error(json.message ?? `Request failed: ${res.status}`);
  return json.data;
}

export async function getMySubmissions(
  token: string,
): Promise<VideoSubmission[]> {
  const res = await fetch(`${BASE_URL}/video-submissions`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  const json = (await res.json()) as ArEnvelope<VideoSubmission[]>;
  if (!res.ok) throw new Error(json.message ?? `Request failed: ${res.status}`);
  return json.data;
}

// ---------------------------------------------------------------------------
// Videos Search API (fetch video details by ID for playlists)
// ---------------------------------------------------------------------------

export type VideoSearchResult = Record<string, unknown>;

export async function getVideosByIds(
  videoIds: string[],
): Promise<VideoSearchResult[]> {
  const results: VideoSearchResult[] = [];
  for (const vid of videoIds) {
    try {
      const res = await fetch(`${VIDEOS_API_URL}/api/videos/query`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-API-KEY": VIDEOS_API_KEY,
        },
        body: JSON.stringify({ video_id: vid }),
      });
      if (res.ok) {
        const json = await res.json();
        const data = json.data ?? json;
        const videos = data.videos ?? [];
        if (videos.length > 0) results.push(videos[0]);
      }
    } catch {
      // skip failed fetches
    }
  }
  return results;
}

// ---------------------------------------------------------------------------
// Onboarding: complete account
// ---------------------------------------------------------------------------

export async function completeOnboardingAccount(
  sessionUuid: string,
  body: CompleteAccountRequestBody
): Promise<CompleteAccountResponse> {
  const res = await fetch(
    `${BASE_URL}/onboarding_sessions/${encodeURIComponent(sessionUuid)}/account`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        first_name: body.first_name.trim(),
        last_name: body.last_name.trim(),
        account_type: body.account_type,
        company_name: body.account_type === "business" ? (body.company_name?.trim() ?? "") : null,
        password: body.password,
        confirm_password: body.confirm_password,
      }),
    }
  );
  const json = (await res.json()) as CompleteAccountResponse & { error_message?: string; detail?: unknown };
  if (!res.ok) {
    if (res.status === 404) {
      throw new Error("No session exists for the provided UUID");
    }
    const msg = json.error_message ?? json.message ?? (Array.isArray(json.detail) ? json.detail.map((d: { msg?: string }) => d.msg).filter(Boolean).join(" ") : undefined) ?? `Request failed: ${res.status}`;
    throw new Error(msg);
  }
  return json;
}
