"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import AuthGuard from "@/components/AuthGuard";
import { apiFetch } from "@/lib/api";

/* ── Types ── */

interface SessionSummary {
  id: number;
  strategy_id: string;
  symbols: string;
  status: string;
  initial_capital: number;
  current_cash: number;
  equity: number;
  total_return_pct: number;
  created_at: string;
}

interface Position {
  symbol: string;
  quantity: number;
  avg_cost: number;
  current_price: number;
  market_value: number;
  unrealized_pnl: number;
  unrealized_pnl_pct: number;
}

interface Order {
  id: number;
  symbol: string;
  action: string;
  quantity: number;
  price: number;
  commission: number;
  status: string;
  created_at: string;
}

interface Alert {
  id: number;
  alert_type: string;
  message: string;
  symbol?: string;
  is_read: boolean;
  created_at: string;
}

interface WsPortfolioUpdate {
  type: "portfolio_update";
  equity: number;
  cash: number;
  drawdown_pct: number;
}

interface WsPositionUpdate {
  type: "position_update";
  positions: Position[];
}

interface WsAlert {
  type: "alert";
  alert_type: string;
  message: string;
  symbol?: string;
}

interface WsOrder {
  type: "order";
  action: string;
  symbol: string;
  quantity: number;
  price: number;
  commission: number;
}

type WsEvent = WsPortfolioUpdate | WsPositionUpdate | WsAlert | WsOrder | { type: string; [key: string]: unknown };

/* ── Component ── */

export default function PaperTradingPage() {
  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<number | null>(null);
  const [positions, setPositions] = useState<Position[]>([]);
  const [orders, setOrders] = useState<Order[]>([]);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [equity, setEquity] = useState<number | null>(null);
  const [cash, setCash] = useState<number | null>(null);
  const [drawdown, setDrawdown] = useState<number>(0);
  const [wsStatus, setWsStatus] = useState<"disconnected" | "connected" | "error">("disconnected");
  const [liveAlerts, setLiveAlerts] = useState<string[]>([]);
  const wsRef = useRef<WebSocket | null>(null);

  // Form state
  const [newStrategyId, setNewStrategyId] = useState("ma_cross");
  const [newSymbols, setNewSymbols] = useState("KRW-BTC,KRW-ETH");
  const [newCapital, setNewCapital] = useState(10000000);
  const [creating, setCreating] = useState(false);

  /* ── Fetch sessions list ── */
  const loadSessions = useCallback(async () => {
    try {
      const data = await apiFetch<SessionSummary[]>("/api/v1/paper-trading/sessions");
      setSessions(data);
    } catch {
      /* ignore */
    }
  }, []);

  useEffect(() => {
    loadSessions();
  }, [loadSessions]);

  /* ── WebSocket connection ── */
  const connectWs = useCallback((sessionId: number) => {
    if (wsRef.current) {
      wsRef.current.close();
    }

    const wsUrl =
      (process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000") +
      `/api/v1/paper-trading/sessions/${sessionId}/ws`;

    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => setWsStatus("connected");
    ws.onerror = () => setWsStatus("error");
    ws.onclose = () => setWsStatus("disconnected");

    ws.onmessage = (evt) => {
      let msg: WsEvent;
      try {
        msg = JSON.parse(evt.data);
      } catch {
        return;
      }

      switch (msg.type) {
        case "init": {
          const init = msg as { type: string; equity: number; cash: number; positions: Position[] };
          setEquity(init.equity);
          setCash(init.cash);
          setPositions(init.positions ?? []);
          break;
        }
        case "portfolio_update": {
          const pu = msg as WsPortfolioUpdate;
          setEquity(pu.equity);
          setCash(pu.cash);
          setDrawdown(pu.drawdown_pct);
          break;
        }
        case "position_update": {
          const pu = msg as WsPositionUpdate;
          setPositions(pu.positions);
          break;
        }
        case "alert": {
          const al = msg as WsAlert;
          setLiveAlerts((prev) => [`[${al.alert_type.toUpperCase()}] ${al.message}`, ...prev.slice(0, 19)]);
          break;
        }
        case "order": {
          const ord = msg as WsOrder;
          setLiveAlerts((prev) => [
            `✅ ${ord.action.toUpperCase()} ${ord.symbol} qty=${ord.quantity.toFixed(6)} @ ${ord.price.toLocaleString()}`,
            ...prev.slice(0, 19),
          ]);
          break;
        }
      }
    };

    return ws;
  }, []);

  /* ── Select a session (load detail + open WS) ── */
  const selectSession = useCallback(
    async (sessionId: number) => {
      setActiveSessionId(sessionId);
      setPositions([]);
      setOrders([]);
      setAlerts([]);
      setLiveAlerts([]);
      setEquity(null);
      setCash(null);
      setDrawdown(0);

      try {
        const [ordersData, alertsData] = await Promise.all([
          apiFetch<Order[]>(`/api/v1/paper-trading/sessions/${sessionId}/orders?limit=30`),
          apiFetch<Alert[]>(`/api/v1/paper-trading/sessions/${sessionId}/alerts?limit=30`),
        ]);
        setOrders(ordersData);
        setAlerts(alertsData);
      } catch {
        /* ignore */
      }

      connectWs(sessionId);
    },
    [connectWs]
  );

  /* ── Create session ── */
  const handleCreate = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();
      setCreating(true);
      try {
        const symbolList = newSymbols.split(",").map((s) => s.trim()).filter(Boolean);
        const session = await apiFetch<SessionSummary>("/api/v1/paper-trading/sessions", {
          method: "POST",
          body: JSON.stringify({
            strategy_id: newStrategyId,
            symbols: symbolList,
            initial_capital: newCapital,
          }),
        });
        setSessions((prev) => [session, ...prev]);
        await selectSession(session.id);
      } catch (err) {
        alert("세션 생성 실패: " + String(err));
      } finally {
        setCreating(false);
      }
    },
    [newStrategyId, newSymbols, newCapital, selectSession]
  );

  /* ── Stop session ── */
  const handleStop = useCallback(async () => {
    if (!activeSessionId) return;
    if (!confirm("세션을 중지하시겠습니까?")) return;
    try {
      await apiFetch(`/api/v1/paper-trading/sessions/${activeSessionId}`, { method: "DELETE" });
      await loadSessions();
      wsRef.current?.close();
      setActiveSessionId(null);
    } catch (err) {
      alert("중지 실패: " + String(err));
    }
  }, [activeSessionId, loadSessions]);

  /* ── Manual tick ── */
  const handleTick = useCallback(async () => {
    if (!activeSessionId) return;
    try {
      await apiFetch(`/api/v1/paper-trading/sessions/${activeSessionId}/tick`, { method: "POST" });
    } catch (err) {
      alert("Tick 오류: " + String(err));
    }
  }, [activeSessionId]);

  const activeSession = sessions.find((s) => s.id === activeSessionId);

  /* ── Render ── */
  return (
    <AuthGuard>
      <div className="p-6 max-w-7xl mx-auto">
        <h1 className="text-2xl font-bold mb-6">모의 투자 (Paper Trading)</h1>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* ── Left: session list + create ── */}
          <div className="space-y-4">
            {/* Create new session form */}
            <div className="bg-slate-800 rounded-lg p-4 border border-slate-700">
              <h2 className="font-semibold mb-3">새 세션 시작</h2>
              <form onSubmit={handleCreate} className="space-y-3">
                <div>
                  <label className="text-xs text-slate-400 block mb-1">전략</label>
                  <select
                    value={newStrategyId}
                    onChange={(e) => setNewStrategyId(e.target.value)}
                    className="w-full bg-slate-700 border border-slate-600 rounded px-2 py-1.5 text-sm"
                  >
                    <option value="ma_cross">MA Cross</option>
                    <option value="rsi">RSI</option>
                    <option value="volume">Volume</option>
                  </select>
                </div>
                <div>
                  <label className="text-xs text-slate-400 block mb-1">심볼 (쉼표 구분)</label>
                  <input
                    value={newSymbols}
                    onChange={(e) => setNewSymbols(e.target.value)}
                    className="w-full bg-slate-700 border border-slate-600 rounded px-2 py-1.5 text-sm"
                    placeholder="KRW-BTC,KRW-ETH"
                  />
                </div>
                <div>
                  <label className="text-xs text-slate-400 block mb-1">초기 자본 (₩)</label>
                  <input
                    type="number"
                    value={newCapital}
                    onChange={(e) => setNewCapital(Number(e.target.value))}
                    className="w-full bg-slate-700 border border-slate-600 rounded px-2 py-1.5 text-sm"
                    min={1000}
                    step={1000000}
                  />
                </div>
                <button
                  type="submit"
                  disabled={creating}
                  className="w-full bg-blue-600 hover:bg-blue-700 disabled:opacity-50 rounded px-3 py-2 text-sm font-semibold"
                >
                  {creating ? "생성 중..." : "시작"}
                </button>
              </form>
            </div>

            {/* Sessions list */}
            <div className="bg-slate-800 rounded-lg border border-slate-700">
              <div className="px-4 py-3 border-b border-slate-700">
                <h2 className="font-semibold text-sm">내 세션</h2>
              </div>
              {sessions.length === 0 ? (
                <p className="p-4 text-slate-500 text-sm">세션 없음</p>
              ) : (
                <ul className="divide-y divide-slate-700">
                  {sessions.map((s) => (
                    <li
                      key={s.id}
                      onClick={() => selectSession(s.id)}
                      className={`px-4 py-3 cursor-pointer hover:bg-slate-700 transition-colors ${
                        s.id === activeSessionId ? "bg-slate-700" : ""
                      }`}
                    >
                      <div className="flex justify-between items-start">
                        <div>
                          <p className="text-sm font-medium">{s.strategy_id}</p>
                          <p className="text-xs text-slate-400">{s.symbols}</p>
                        </div>
                        <span
                          className={`text-xs px-1.5 py-0.5 rounded ${
                            s.status === "active"
                              ? "bg-green-900 text-green-300"
                              : "bg-slate-700 text-slate-400"
                          }`}
                        >
                          {s.status}
                        </span>
                      </div>
                      <div className="mt-1 flex gap-3 text-xs">
                        <span className="text-slate-400">
                          ₩{s.equity.toLocaleString()}
                        </span>
                        <span
                          className={
                            s.total_return_pct >= 0 ? "text-green-400" : "text-red-400"
                          }
                        >
                          {s.total_return_pct >= 0 ? "+" : ""}
                          {s.total_return_pct.toFixed(2)}%
                        </span>
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>

          {/* ── Right: active session detail ── */}
          <div className="lg:col-span-2 space-y-4">
            {!activeSessionId ? (
              <div className="bg-slate-800 rounded-lg p-8 border border-slate-700 text-center text-slate-500">
                세션을 선택하거나 새로 만드세요
              </div>
            ) : (
              <>
                {/* Portfolio summary */}
                <div className="bg-slate-800 rounded-lg p-4 border border-slate-700">
                  <div className="flex justify-between items-center mb-4">
                    <div className="flex items-center gap-3">
                      <h2 className="font-semibold">포트폴리오 현황</h2>
                      <span
                        className={`text-xs px-2 py-0.5 rounded-full ${
                          wsStatus === "connected"
                            ? "bg-green-900 text-green-300"
                            : wsStatus === "error"
                            ? "bg-red-900 text-red-300"
                            : "bg-slate-700 text-slate-400"
                        }`}
                      >
                        {wsStatus === "connected" ? "● 연결됨" : wsStatus === "error" ? "● 오류" : "○ 연결 안됨"}
                      </span>
                    </div>
                    <div className="flex gap-2">
                      {activeSession?.status === "active" && (
                        <>
                          <button
                            onClick={handleTick}
                            className="text-xs bg-slate-700 hover:bg-slate-600 px-3 py-1.5 rounded"
                          >
                            수동 틱
                          </button>
                          <button
                            onClick={handleStop}
                            className="text-xs bg-red-900 hover:bg-red-800 px-3 py-1.5 rounded"
                          >
                            세션 중지
                          </button>
                        </>
                      )}
                    </div>
                  </div>

                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                    {[
                      {
                        label: "총 자산",
                        value: equity !== null ? `₩${equity.toLocaleString()}` : "—",
                      },
                      {
                        label: "가용 현금",
                        value: cash !== null ? `₩${cash.toLocaleString()}` : "—",
                      },
                      {
                        label: "초기 자본",
                        value: activeSession ? `₩${activeSession.initial_capital.toLocaleString()}` : "—",
                      },
                      {
                        label: "낙폭",
                        value: `${drawdown.toFixed(2)}%`,
                        className: drawdown > 5 ? "text-red-400" : "text-slate-200",
                      },
                    ].map((stat) => (
                      <div key={stat.label} className="bg-slate-700 rounded p-3">
                        <p className="text-xs text-slate-400">{stat.label}</p>
                        <p className={`text-base font-semibold mt-1 ${stat.className ?? ""}`}>
                          {stat.value}
                        </p>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Positions */}
                <div className="bg-slate-800 rounded-lg border border-slate-700">
                  <div className="px-4 py-3 border-b border-slate-700">
                    <h2 className="font-semibold text-sm">보유 포지션</h2>
                  </div>
                  {positions.filter((p) => p.quantity > 0).length === 0 ? (
                    <p className="p-4 text-slate-500 text-sm">보유 포지션 없음</p>
                  ) : (
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="text-xs text-slate-400 border-b border-slate-700">
                          <th className="text-left px-4 py-2">심볼</th>
                          <th className="text-right px-4 py-2">수량</th>
                          <th className="text-right px-4 py-2">평균단가</th>
                          <th className="text-right px-4 py-2">현재가</th>
                          <th className="text-right px-4 py-2">평가금액</th>
                          <th className="text-right px-4 py-2">미실현손익</th>
                        </tr>
                      </thead>
                      <tbody>
                        {positions
                          .filter((p) => p.quantity > 0)
                          .map((p) => (
                            <tr key={p.symbol} className="border-b border-slate-700 last:border-0">
                              <td className="px-4 py-2 font-medium">{p.symbol}</td>
                              <td className="px-4 py-2 text-right text-slate-300">
                                {p.quantity.toFixed(6)}
                              </td>
                              <td className="px-4 py-2 text-right text-slate-300">
                                ₩{p.avg_cost.toLocaleString()}
                              </td>
                              <td className="px-4 py-2 text-right text-slate-300">
                                ₩{p.current_price.toLocaleString()}
                              </td>
                              <td className="px-4 py-2 text-right">
                                ₩{p.market_value.toLocaleString()}
                              </td>
                              <td
                                className={`px-4 py-2 text-right font-semibold ${
                                  p.unrealized_pnl >= 0 ? "text-green-400" : "text-red-400"
                                }`}
                              >
                                {p.unrealized_pnl >= 0 ? "+" : ""}₩
                                {p.unrealized_pnl.toLocaleString(undefined, { maximumFractionDigits: 0 })}{" "}
                                <span className="text-xs font-normal">
                                  ({p.unrealized_pnl_pct >= 0 ? "+" : ""}
                                  {p.unrealized_pnl_pct.toFixed(2)}%)
                                </span>
                              </td>
                            </tr>
                          ))}
                      </tbody>
                    </table>
                  )}
                </div>

                {/* Live alerts + order history side by side */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  {/* Live event feed */}
                  <div className="bg-slate-800 rounded-lg border border-slate-700">
                    <div className="px-4 py-3 border-b border-slate-700">
                      <h2 className="font-semibold text-sm">실시간 알림</h2>
                    </div>
                    <ul className="divide-y divide-slate-700 max-h-48 overflow-y-auto">
                      {liveAlerts.length === 0 ? (
                        <li className="p-3 text-slate-500 text-xs">알림 없음</li>
                      ) : (
                        liveAlerts.map((msg, i) => (
                          <li
                            key={i}
                            className={`p-3 text-xs ${
                              msg.includes("RISK") || msg.includes("WARNING") || msg.includes("CRITICAL")
                                ? "text-red-400"
                                : msg.includes("SIGNAL")
                                ? "text-yellow-400"
                                : "text-slate-300"
                            }`}
                          >
                            {msg}
                          </li>
                        ))
                      )}
                    </ul>
                  </div>

                  {/* Recent orders */}
                  <div className="bg-slate-800 rounded-lg border border-slate-700">
                    <div className="px-4 py-3 border-b border-slate-700">
                      <h2 className="font-semibold text-sm">최근 주문</h2>
                    </div>
                    <ul className="divide-y divide-slate-700 max-h-48 overflow-y-auto">
                      {orders.length === 0 ? (
                        <li className="p-3 text-slate-500 text-xs">주문 없음</li>
                      ) : (
                        orders.slice(0, 15).map((o) => (
                          <li key={o.id} className="p-3 text-xs flex justify-between">
                            <div>
                              <span
                                className={`font-semibold mr-1 ${
                                  o.action === "buy" ? "text-green-400" : "text-red-400"
                                }`}
                              >
                                {o.action.toUpperCase()}
                              </span>
                              {o.symbol}
                            </div>
                            <div className="text-right text-slate-400">
                              <div>₩{o.price.toLocaleString()}</div>
                              <div className="text-slate-500">
                                {new Date(o.created_at).toLocaleString("ko-KR", {
                                  month: "2-digit",
                                  day: "2-digit",
                                  hour: "2-digit",
                                  minute: "2-digit",
                                })}
                              </div>
                            </div>
                          </li>
                        ))
                      )}
                    </ul>
                  </div>
                </div>

                {/* Risk alerts from DB */}
                {alerts.filter((a) => a.alert_type === "risk").length > 0 && (
                  <div className="bg-red-950 border border-red-800 rounded-lg p-4">
                    <h2 className="font-semibold text-red-300 text-sm mb-2">⚠ 리스크 경고</h2>
                    <ul className="space-y-1">
                      {alerts
                        .filter((a) => a.alert_type === "risk")
                        .slice(0, 5)
                        .map((a) => (
                          <li key={a.id} className="text-xs text-red-300">
                            {a.message}
                          </li>
                        ))}
                    </ul>
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      </div>
    </AuthGuard>
  );
}
