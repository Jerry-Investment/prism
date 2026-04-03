import api from "./api";

export interface AuthUser {
  id: number;
  email: string;
  full_name: string | null;
  is_active: boolean;
  created_at: string | null;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export async function signup(email: string, password: string, fullName?: string): Promise<TokenResponse> {
  const { data } = await api.post<TokenResponse>("/api/v1/auth/signup", {
    email,
    password,
    full_name: fullName ?? null,
  });
  return data;
}

export async function login(email: string, password: string): Promise<TokenResponse> {
  const { data } = await api.post<TokenResponse>("/api/v1/auth/login", { email, password });
  return data;
}

export async function getMe(): Promise<AuthUser> {
  const { data } = await api.get<AuthUser>("/api/v1/auth/me");
  return data;
}
