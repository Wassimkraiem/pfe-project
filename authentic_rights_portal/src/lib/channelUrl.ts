/**
 * URL helpers for channel/social profile inputs.
 * Sanitization keeps only allowed query params to avoid tracking/unsafe params.
 */

/** Query param keys to KEEP when sanitizing channel URLs; all others are stripped. */
export const ALLOWED_QUERY_PARAMS = ["id", "profile_id", "channel_id"] as const;

/**
 * Sanitize a channel URL: keep only origin, pathname, and allowed query params
 * (id, profile_id, channel_id). All other query params are removed.
 *
 * @example
 * // Input (e.g. paste from browser):
 * "https://instagram.com/user?utm_source=foo&id=123&profile_id=456&channel_id=789&other=strip"
 * // Output:
 * "https://instagram.com/user?id=123&profile_id=456&channel_id=789"
 *
 * Test example to paste in "Social Profile or Website URL" (signup or contact pages step 2):
 * https://instagram.com/username?utm_source=email&id=12345&profile_id=67890&channel_id=abc&foo=bar
 * → sanitized to: https://instagram.com/username?id=12345&profile_id=67890&channel_id=abc
 */
export function sanitizeChannelUrl(url: string): string {
  try {
    const u = new URL(url);
    const allowed = new URLSearchParams();
    for (const key of ALLOWED_QUERY_PARAMS) {
      const value = u.searchParams.get(key);
      if (value != null && value !== "") allowed.set(key, value);
    }
    u.search = allowed.toString();
    return u.toString();
  } catch {
    return url;
  }
}

/** Normalize input to a valid HTTPS URL (add or upgrade to https). */
export function normalizeToHttps(val: string): string {
  const s = val.trim();
  if (s.toLowerCase().startsWith("https://")) return s;
  if (s.toLowerCase().startsWith("http://")) return "https://" + s.slice(7);
  return "https://" + s;
}

/** Normalize channel URL for comparison (e.g. with custom_quote_triggers). */
export function normalizeChannelUrlForCompare(url: string): string {
  const s = url.trim().toLowerCase();
  return s.endsWith("/") ? s.slice(0, -1) : s;
}
