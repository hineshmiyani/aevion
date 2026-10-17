// Shared by the API proxy routes. The Aevion API rate-limits per visitor but sees this
// server's IP for everyone, so we pass the visitor's IP along with the shared secret that
// tells the API to trust it (apps/api/src/aevion/api/limits.py).
export function visitorHeaders(request: Request): Record<string, string> {
  const secret = process.env.AEVION_PROXY_SECRET;
  const ip = request.headers.get("x-real-ip") ?? request.headers.get("x-forwarded-for")?.split(",")[0]?.trim();
  return secret && ip ? { "X-Aevion-Client-IP": ip, "X-Aevion-Proxy-Secret": secret } : {};
}

export function apiBase(): string | null {
  const api = process.env.AEVION_API_URL;
  return api ? api.replace(/\/$/, "") : null;
}
