"use client";

import { useState, useEffect } from "react";

interface Strategy {
  id: string;
  name: string;
  description: string;
  type: string;
  parameters: Record<string, unknown>;
}

export default function StrategiesPage() {
  const [strategies, setStrategies] = useState<Strategy[]>([]);
  const [name, setName] = useState("");
  const [type, setType] = useState("ma_cross");

  useEffect(() => {
    fetch("/api/v1/strategies/")
      .then((r) => r.json())
      .then(setStrategies)
      .catch(() => {});
  }, []);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    const res = await fetch("/api/v1/strategies/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, type, description: "", parameters: {} }),
    });
    const s = await res.json();
    setStrategies((prev) => [...prev, s]);
    setName("");
  }

  return (
    <div className="p-8 max-w-3xl">
      <h1 className="text-2xl font-bold mb-6">전략 관리</h1>
      <form onSubmit={handleCreate} className="flex gap-3 mb-8">
        <input
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="전략 이름"
          className="flex-1 bg-slate-800 border border-slate-600 rounded px-3 py-2"
          required
        />
        <select
          value={type}
          onChange={(e) => setType(e.target.value)}
          className="bg-slate-800 border border-slate-600 rounded px-3 py-2"
        >
          <option value="ma_cross">MA Cross</option>
          <option value="rsi">RSI</option>
          <option value="volume">Volume</option>
        </select>
        <button type="submit" className="bg-green-500 hover:bg-green-400 text-white font-semibold px-4 py-2 rounded">
          추가
        </button>
      </form>

      <div className="space-y-3">
        {strategies.map((s) => (
          <div key={s.id} className="bg-slate-800 rounded-lg p-4 border border-slate-700">
            <p className="font-semibold">{s.name}</p>
            <p className="text-slate-400 text-sm mt-1">{s.type}</p>
          </div>
        ))}
        {strategies.length === 0 && <p className="text-slate-500 text-sm">등록된 전략이 없습니다.</p>}
      </div>
    </div>
  );
}
