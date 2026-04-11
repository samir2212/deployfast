const API_URL =
  import.meta.env.VITE_API_URL || "https://api.ai-deploy.tutaia.com";

// ─── Payment / Subscription types ───────────
export interface SubscriptionStatus {
  active: boolean;
  plan: "starter" | "builder" | null;
  app_limit: number;
  apps_used: number;
}

export interface CheckoutSession {
  checkout_url: string;
}

export interface PaymentVerification {
  success: boolean;
  plan: string;
}

export interface App {
  id: string;
  name: string;
  status: "building" | "running" | "failed";
  url?: string;
  created_at: string;
}

async function authFetch(
  path: string,
  token: string,
  options: RequestInit = {}
) {
  const res = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: {
      Authorization: `Bearer ${token}`,
      ...options.headers,
    },
  });
  if (!res.ok) {
    const text = await res.text().catch(() => "Unknown error");
    throw new Error(`API error ${res.status}: ${text}`);
  }
  return res.json();
}

export async function listApps(token: string): Promise<App[]> {
  return authFetch("/api/apps/", token);
}

export async function getApp(id: string, token: string): Promise<App> {
  return authFetch(`/api/apps/${id}`, token);
}

export async function deployApp(
  file: File,
  name: string,
  token: string,
  subdomain: string,
  envVars: Record<string, string> = {}
): Promise<App> {
  const form = new FormData();
  form.append("file", file);
  form.append("name", name);
  form.append("subdomain", subdomain);
  form.append("env_vars", JSON.stringify(envVars));

  const res = await fetch(`${API_URL}/api/apps/`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: form,
  });

  if (!res.ok) {
    const text = await res.text().catch(() => "Unknown error");
    throw new Error(`Deploy failed: ${text}`);
  }
  return res.json();
}

// ─── Payment API ────────────────────────────

export async function createCheckoutSession(
  priceId: string,
  userId: string,
  token: string
): Promise<CheckoutSession> {
  return authFetch("/api/payments/create-checkout-session", token, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ price_id: priceId, user_id: userId }),
  });
}

export async function getSubscriptionStatus(
  token: string
): Promise<SubscriptionStatus> {
  return authFetch("/api/payments/subscription-status", token);
}

export async function verifyPayment(
  sessionId: string,
  token: string
): Promise<PaymentVerification> {
  return authFetch(`/api/payments/verify?session_id=${sessionId}`, token);
}

export async function deleteApp(
  id: string,
  token: string
): Promise<void> {
  const res = await fetch(`${API_URL}/api/apps/${id}`, {
    method: "DELETE",
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) {
    const text = await res.text().catch(() => "Unknown error");
    throw new Error(`Delete failed: ${text}`);
  }
}
