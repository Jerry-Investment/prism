import Link from "next/link";

export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-8">
      <div className="text-center mb-12">
        <h1 className="text-5xl font-bold text-green-400 mb-3">PRISM</h1>
        <p className="text-slate-400 text-lg">Portfolio Research &amp; Investment Simulation Machine</p>
      </div>

      {/* Auth CTA */}
      <div className="flex gap-4 mb-12">
        <Link
          href="/login"
          className="px-6 py-3 bg-slate-800 border border-slate-600 hover:border-green-500 text-slate-100 font-semibold rounded-lg transition-colors"
        >
          로그인
        </Link>
        <Link
          href="/signup"
          className="px-6 py-3 bg-green-600 hover:bg-green-500 text-white font-semibold rounded-lg transition-colors"
        >
          무료로 시작하기
        </Link>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 w-full max-w-4xl">
        <Link href="/dashboard" className="group block p-6 bg-slate-800 rounded-xl border border-slate-700 hover:border-green-500 transition-colors">
          <h2 className="text-xl font-semibold mb-2 group-hover:text-green-400">Dashboard</h2>
          <p className="text-slate-400 text-sm">포트폴리오 현황 및 성과 요약</p>
        </Link>

        <Link href="/backtest" className="group block p-6 bg-slate-800 rounded-xl border border-slate-700 hover:border-green-500 transition-colors">
          <h2 className="text-xl font-semibold mb-2 group-hover:text-green-400">Backtest</h2>
          <p className="text-slate-400 text-sm">전략 백테스트 실행 및 결과 조회</p>
        </Link>

        <Link href="/strategies" className="group block p-6 bg-slate-800 rounded-xl border border-slate-700 hover:border-green-500 transition-colors">
          <h2 className="text-xl font-semibold mb-2 group-hover:text-green-400">Strategies</h2>
          <p className="text-slate-400 text-sm">전략 생성, 편집, 관리</p>
        </Link>
      </div>
    </main>
  );
}
