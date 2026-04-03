"use client";

export default function DashboardPage() {
  return (
    <div className="p-8">
      <h1 className="text-2xl font-bold mb-6">Dashboard</h1>
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
      <p className="text-slate-500 text-sm">Phase 2에서 실시간 데이터 연동 예정</p>
    </div>
  );
}
