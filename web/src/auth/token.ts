/**
 * Reads the public expiration claim from a JWT without validating its signature.
 * Signature validation remains the API's responsibility; this is only a local UX
 * guard so the browser can stop using a token it already knows has expired.
 */
export function getTokenExpirationTime(token: string): number | null {
  const payload = token.split(".")[1];
  if (!payload) return null;

  try {
    const normalized = payload.replace(/-/g, "+").replace(/_/g, "/");
    const padding = "=".repeat((4 - (normalized.length % 4)) % 4);
    const decoded: unknown = JSON.parse(atob(normalized + padding));
    if (!decoded || typeof decoded !== "object" || !("exp" in decoded)) return null;

    const expirationSeconds = (decoded as { exp?: unknown }).exp;
    return typeof expirationSeconds === "number" && Number.isFinite(expirationSeconds)
      ? expirationSeconds * 1000
      : null;
  } catch {
    return null;
  }
}

export function isTokenExpired(token: string, now = Date.now()): boolean {
  const expirationTime = getTokenExpirationTime(token);
  return expirationTime !== null && now >= expirationTime;
}
