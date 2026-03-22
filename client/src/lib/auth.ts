const BASE = "/api/auth";

export interface AuthUser {
  id: string;
  email: string;
  full_name: string;
  avatar_url?: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  user: AuthUser;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });

  const data = await res.json().catch(() => ({}));

  if (!res.ok) {
    throw new Error(data?.detail ?? `Request failed (${res.status})`);
  }

  return data as T;
}

export const authApi = {
  register: (email: string, password: string, full_name: string) =>
    request<{ message?: string; email: string; pending_verification?: boolean }>("/register", {
      method: "POST",
      body: JSON.stringify({ email, password, full_name }),
    }),

  login: (email: string, password: string) =>
    request<LoginResponse>("/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),

  resendVerification: (email: string) =>
    request<{ message: string }>("/resend-verification", {
      method: "POST",
      body: JSON.stringify({ email }),
    }),

  updateProfile: (token: string, body: { full_name?: string; avatar_url?: string }) =>
    fetch(`${BASE}/profile`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
      body: JSON.stringify(body),
    }).then(async res => {
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data?.detail ?? `Request failed (${res.status})`);
      return data as AuthUser;
    }),
};

