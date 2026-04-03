"use client";

import { useState } from "react";

export default function BacktestPage() {
  const [symbol, setSymbol] = useState("KRW-BTC");
  const [interval, setInterval] = useState("1d");
  const [status, setStatus] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setStatus("백테스트 제출 중...");
    try {
      const res = await fetch("/api/v1/backtest/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          strategy_id: "demo",
          symbol,
          interval,
          start: "2024-01-01",
          end: "2024-12-31",
          initial_capital: 10000000,
        }),
      });
      const data = await res.json();
      setStatus(`작업 ID: ${data.task_id} (${data.status})`);
    } catch {
      setStatus("오류 발생");
    }
  }

  return (
    <div className="p-8 max-w-2xl">
      <h1 className="text-2xl font-bold mb-6">백테스트 실행</h1>
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-sm text-slate-400 mb-1">심볼</label>
          <select
            value={symbol}
            onChange={(e) => setSymbol(e.target.value)}
            className="w-full bg-slate-800 border border-slate-600 rounded px-3 py-2"
          >
            <option>KRW-BTC</option>
            <option>KRW-ETH</option>
            <option>KRW-XRP</option>
          </select>
        </div>
        <div>
          <label className="block text-sm text-slate-400 mb-1">인터벌</label>
          <select
            value={interval}
            onChange={(e) => setInterval(e.target.value)}
            className="w-full bg-slate-800 border border-slate-600 rounded px-3 py-2"
          >
            <option value="1d">1일</option>
            <option value="4h">4시간</option>
            <option value="1h">1시간</option>
          </select>
        </div>
        <button
          type="submit"
          className="bg-green-500 hover:bg-green-400 text-white font-semibold px-6 py-2 rounded transition-colors"
        >
          실행
        </button>
      </form>
      {status && <p className="mt-4 text-slate-300 text-sm">{status}</p>}
    </div>
  );
}
