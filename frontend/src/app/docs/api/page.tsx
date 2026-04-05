import Link from "next/link";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "API 문서 — PRISM",
  description: "PRISM REST API 레퍼런스. 인증, 백테스트, 전략, 모의 투자 엔드포인트 완전 가이드.",
};

const ENDPOINTS = [
  {
    tag: "인증 (Auth)",
    base: "/api/v1/auth",
    routes: [
      { method: "POST", path: "/signup", desc: "새 계정 생성", body: "email, password, full_name?" },
      { method: "POST", path: "/login", desc: "로그인 (JWT 발급)", body: "email, password" },
      { method: "GET", path: "/me", desc: "현재 사용자 정보 조회", auth: true },
    ],
  },
  {
    tag: "전략 (Strategies)",
    base: "/api/v1/strategies",
    routes: [
      { method: "GET", path: "/", desc: "전략 목록 조회", auth: true },
      { method: "POST", path: "/", desc: "전략 생성", auth: true, body: "name, description?, config" },
      { method: "GET", path: "/{id}", desc: "전략 단건 조회", auth: true },
      { method: "PUT", path: "/{id}", desc: "전략 수정", auth: true },
      { method: "DELETE", path: "/{id}", desc: "전략 삭제", auth: true },
    ],
  },
  {
    tag: "백테스트 (Backtest)",
    base: "/api/v1/backtest",
    routes: [
      { method: "POST", path: "/run", desc: "백테스트 실행", auth: true, body: "strategy_id, symbol, start_date, end_date, initial_capital, commission_rate?" },
      { method: "GET", path: "/results", desc: "백테스트 결과 목록", auth: true },
      { method: "GET", path: "/results/{id}", desc: "백테스트 결과 단건 조회", auth: true },
    ],
  },
  {
    tag: "시장 데이터 (Market Data)",
    base: "/api/v1/market-data",
    routes: [
      { method: "GET", path: "/ohlcv", desc: "OHLCV 데이터 조회", auth: true, query: "symbol, start, end, interval?" },
      { method: "GET", path: "/symbols", desc: "지원 종목 목록", auth: true },
    ],
  },
  {
    tag: "분석 (Analytics)",
    base: "/api/v1/analytics",
    routes: [
      { method: "POST", path: "/report", desc: "성과 리포트 생성", auth: true, body: "backtest_result_id" },
      { method: "GET", path: "/report/{id}", desc: "리포트 조회", auth: true },
    ],
  },
  {
    tag: "전략 비교 (Comparison)",
    base: "/api/v1/comparison",
    routes: [
      { method: "POST", path: "/", desc: "전략 비교 분석", auth: true, body: "backtest_result_ids[]" },
    ],
  },
  {
    tag: "모의 투자 (Paper Trading)",
    base: "/api/v1/paper-trading",
    routes: [
      { method: "GET", path: "/sessions", desc: "모의 투자 세션 목록", auth: true },
      { method: "POST", path: "/sessions", desc: "새 세션 생성", auth: true, body: "strategy_id, symbol, initial_capital" },
      { method: "GET", path: "/sessions/{id}", desc: "세션 상태 조회", auth: true },
      { method: "POST", path: "/sessions/{id}/start", desc: "세션 시작", auth: true },
      { method: "POST", path: "/sessions/{id}/stop", desc: "세션 중지", auth: true },
      { method: "GET", path: "/sessions/{id}/positions", desc: "포지션 조회", auth: true },
      { method: "GET", path: "/sessions/{id}/orders", desc: "주문 내역 조회", auth: true },
      { method: "GET", path: "/sessions/{id}/alerts", desc: "알림 목록", auth: true },
      { method: "POST", path: "/sessions/{id}/alerts", desc: "알림 설정", auth: true, body: "type, threshold" },
    ],
  },
];

const METHOD_COLORS: Record<string, string> = {
  GET: "bg-blue-900/40 text-blue-400 border-blue-700/50",
  POST: "bg-green-900/40 text-green-400 border-green-700/50",
  PUT: "bg-yellow-900/40 text-yellow-400 border-yellow-700/50",
  DELETE: "bg-red-900/40 text-red-400 border-red-700/50",
};

export default function ApiDocsPage() {
  return (
    <div className="min-h-screen bg-slate-900 text-slate-100">
      {/* Nav */}
      <nav className="border-b border-slate-800 px-6 py-4 flex items-center justify-between">
        <Link href="/" className="text-xl font-bold text-green-400">PRISM</Link>
        <div className="flex items-center gap-6 text-sm text-slate-400">
          <Link href="/docs" className="hover:text-slate-100 transition-colors">사용자 가이드</Link>
          <Link href="/help" className="hover:text-slate-100 transition-colors">FAQ</Link>
          <Link href="/login" className="hover:text-slate-100 transition-colors">로그인</Link>
        </div>
      </nav>

      <div className="max-w-4xl mx-auto px-6 py-16">
        <div className="mb-12">
          <h1 className="text-4xl font-bold mb-3">API 문서</h1>
          <p className="text-slate-400 leading-relaxed mb-6">
            PRISM REST API를 사용하면 백테스트 실행, 전략 관리, 모의 투자 세션 제어를 외부 시스템에서 자동화할 수 있습니다.
          </p>
          <div className="bg-slate-800 border border-slate-700 rounded-xl p-5">
            <div className="font-semibold mb-2 text-sm text-slate-300">Base URL</div>
            <code className="text-green-400 text-sm">https://api.prism.kr</code>
            <div className="mt-4 font-semibold mb-2 text-sm text-slate-300">인터랙티브 문서 (Swagger)</div>
            <code className="text-green-400 text-sm">https://api.prism.kr/docs</code>
            <div className="mt-4 font-semibold mb-2 text-sm text-slate-300">ReDoc</div>
            <code className="text-green-400 text-sm">https://api.prism.kr/redoc</code>
          </div>
        </div>

        {/* Authentication */}
        <section className="mb-12">
          <h2 className="text-2xl font-bold mb-4">인증</h2>
          <p className="text-slate-400 text-sm leading-relaxed mb-4">
            대부분의 엔드포인트는 JWT Bearer 토큰 인증이 필요합니다.
            <code className="bg-slate-800 px-1.5 py-0.5 rounded text-green-400 mx-1">/auth/login</code>
            으로 토큰을 발급받은 후, 모든 요청 헤더에 포함하세요.
          </p>
          <div className="bg-slate-800 border border-slate-700 rounded-xl p-4 font-mono text-sm overflow-x-auto">
            <pre className="text-slate-300">{`Authorization: Bearer <your-jwt-token>`}</pre>
          </div>

          <div className="mt-4 bg-slate-800 border border-slate-700 rounded-xl p-4 font-mono text-sm overflow-x-auto">
            <div className="text-slate-500 mb-2"># 로그인 예시 (curl)</div>
            <pre className="text-slate-300">{`curl -X POST https://api.prism.kr/api/v1/auth/login \\
  -H "Content-Type: application/json" \\
  -d '{"email": "you@example.com", "password": "yourpassword"}'`}</pre>
          </div>
        </section>

        {/* Endpoints */}
        <section>
          <h2 className="text-2xl font-bold mb-6">엔드포인트</h2>
          <div className="space-y-10">
            {ENDPOINTS.map((group) => (
              <div key={group.tag}>
                <h3 className="text-lg font-semibold mb-3 text-green-400">{group.tag}</h3>
                <div className="text-xs text-slate-500 mb-3 font-mono">Base: {group.base}</div>
                <div className="space-y-2">
                  {group.routes.map((route) => (
                    <div
                      key={`${route.method}-${route.path}`}
                      className="bg-slate-800 border border-slate-700 rounded-xl p-4"
                    >
                      <div className="flex items-center gap-3 flex-wrap">
                        <span
                          className={`px-2 py-0.5 rounded border text-xs font-bold font-mono ${
                            METHOD_COLORS[route.method] ?? "bg-slate-700 text-slate-300"
                          }`}
                        >
                          {route.method}
                        </span>
                        <code className="text-slate-300 text-sm font-mono">
                          {group.base}{route.path}
                        </code>
                        {route.auth && (
                          <span className="text-xs text-yellow-500 border border-yellow-700/50 px-1.5 py-0.5 rounded">
                            🔒 인증 필요
                          </span>
                        )}
                      </div>
                      <div className="mt-2 text-slate-400 text-sm">{route.desc}</div>
                      {route.body && (
                        <div className="mt-2 text-xs text-slate-500">
                          <span className="text-slate-400">Body: </span>
                          <code>{route.body}</code>
                        </div>
                      )}
                      {route.query && (
                        <div className="mt-1 text-xs text-slate-500">
                          <span className="text-slate-400">Query: </span>
                          <code>{route.query}</code>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* Rate Limits */}
        <section className="mt-12">
          <h2 className="text-2xl font-bold mb-4">요청 제한 (Rate Limits)</h2>
          <div className="space-y-2 text-sm">
            {[
              { plan: "무료", limit: "분당 20 요청, 백테스트 월 50회" },
              { plan: "Pro", limit: "분당 100 요청, 백테스트 무제한" },
              { plan: "팀", limit: "분당 500 요청, 백테스트 무제한" },
            ].map((row) => (
              <div key={row.plan} className="flex gap-3 bg-slate-800 rounded-lg px-4 py-2.5 border border-slate-700">
                <span className="text-green-400 font-semibold w-16 shrink-0">{row.plan}</span>
                <span className="text-slate-400">{row.limit}</span>
              </div>
            ))}
          </div>
          <p className="text-slate-500 text-xs mt-3">
            제한 초과 시 <code className="text-slate-400">429 Too Many Requests</code> 응답을 반환합니다.
          </p>
        </section>

        {/* Links */}
        <div className="mt-12 bg-slate-800 rounded-2xl border border-slate-700 p-6 flex flex-col sm:flex-row gap-4 items-start sm:items-center justify-between">
          <div>
            <div className="font-semibold mb-1">인터랙티브 API 탐색기</div>
            <div className="text-slate-400 text-sm">Swagger UI에서 직접 API를 테스트해보세요.</div>
          </div>
          <a
            href="https://api.prism.kr/docs"
            target="_blank"
            rel="noopener noreferrer"
            className="px-5 py-2.5 bg-green-600 hover:bg-green-500 text-white rounded-lg text-sm font-semibold transition-colors shrink-0"
          >
            Swagger UI 열기 →
          </a>
        </div>
      </div>

      {/* Footer */}
      <footer className="border-t border-slate-800 px-6 py-6 text-center text-xs text-slate-600">
        <Link href="/" className="hover:text-slate-400 transition-colors">홈</Link>
        {" · "}
        <Link href="/docs" className="hover:text-slate-400 transition-colors">사용자 가이드</Link>
        {" · "}
        <Link href="/help" className="hover:text-slate-400 transition-colors">FAQ</Link>
      </footer>
    </div>
  );
}
