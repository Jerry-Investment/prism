import axios from "axios";

const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000",
  headers: { "Content-Type": "application/json" },
});

// Attach Bearer token from localStorage on every request
api.interceptors.request.use((config) => {
  if (typeof window !== "undefined") {
    const token = localStorage.getItem("prism_token");
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
  }
  return config;
});

export default api;

// Legacy fetch-based helpers kept for backward compatibility
const BASE = process.env.NEXT_PUBLIC_API_URL || "";

export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const token = typeof window !== "undefined" ? localStorage.getItem("prism_token") : null;
  const res = await fetch(`${BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...init?.headers,
    },
  });
  if (!res.ok) {
    const err = await res.text();
    throw new Error(err || res.statusText);
  }
  return res.json();
}

export const apiHelpers = {
  strategies: {
    list: () => apiFetch<import("@/types").Strategy[]>("/api/v1/strategies/"),
    create: (data: Omit<import("@/types").Strategy, "id">) =>
      apiFetch<import("@/types").Strategy>("/api/v1/strategies/", {
        method: "POST",
        body: JSON.stringify(data),
      }),
  },
  backtest: {
    submit: (data: import("@/types").BacktestRequest) =>
      apiFetch<{ task_id: string; status: string }>("/api/v1/backtest/", {
        method: "POST",
        body: JSON.stringify(data),
      }),
    status: (taskId: string) =>
      apiFetch<{ task_id: string; status: string; result: import("@/types").BacktestResult | null }>(
        `/api/v1/backtest/${taskId}`
      ),
  },
  marketData: {
    ohlcv: (symbol: string, interval = "1d", limit = 200) =>
      apiFetch<import("@/types").OHLCVBar[]>(
        `/api/v1/market-data/ohlcv?symbol=${symbol}&interval=${interval}&limit=${limit}`
      ),
  },
};
