"use client";

import { useEffect } from "react";
import { useAuthStore } from "@/lib/authStore";
import { getMe } from "@/lib/auth";
import AuthGuard from "@/components/AuthGuard";
import Link from "next/link";

export default function DashboardPage() {
  const user = useAuthStore((s) => s.user);
  const token = useAuthStore((s) => s.token);
  const setAuth = useAuthStore((s) => s.setAuth);
  const logout = useAuthStore((s) => s.logout);

  // Hydrate user data if we have a token but no user yet (e.g. after page refresh)
  useEffect(() => {
    if (token && !user) {
      getMe()
        .then((u) => setAuth(u, token))
        .catch(() => logout());
    }
  }, [token, user, setAuth, logout]);

  return (
    <AuthGuard>
      <div className="p-8">
        {/* User header */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-2xl font-bold">Dashboard</h1>
            {user && (
              <p className="text-slate-400 text-sm mt-1">
                {user.full_name ? `${user.full_name} (${user.email})` : user.email}
              </p>
            )}
          </div>
          <button
            onClick={logout}
            className="text-sm text-slate-400 hover:text-red-400 transition-colors"
          >
            로그아웃
          </button>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
          {[
            { label: "총 자산", value: "₩10,000,000" },
            { label: "총 수익률", value: "+0.00%" },
            { label: "Sharpe Ratio", value: "—" },
            { label: "최대 낙폭", value: "—" },
          ].map((stat) => (
            <div key={stat.label} className="bg-slate-800 rounded-lg p-4 border border-slate-700">
              <p className="text-slate-400 text-sm">{stat.label}</p>
              <p className="text-xl font-semibold mt-1">{stat.value}</p>
            </div>
          ))}
        </div>

        {/* Navigation shortcuts */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[
            { label: "백테스트", href: "/backtest", desc: "전략 시뮬레이션" },
            { label: "전략 관리", href: "/strategies", desc: "전략 등록/수정" },
            { label: "모의 투자", href: "/paper-trading", desc: "실시간 가상 매매" },
            { label: "분석", href: "/analytics", desc: "성과 리포트" },
          ].map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className="bg-slate-800 hover:bg-slate-700 border border-slate-700 rounded-lg p-4 transition-colors"
            >
              <p className="font-semibold">{item.label}</p>
              <p className="text-slate-400 text-sm mt-1">{item.desc}</p>
            </Link>
          ))}
        </div>
      </div>
    </AuthGuard>
  );
}
