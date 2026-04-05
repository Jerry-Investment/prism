import Link from "next/link";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "사용자 가이드 — PRISM",
  description: "PRISM 백테스트 플랫폼 사용자 가이드. 전략 작성, 백테스트 실행, 모의 투자까지 단계별로 안내합니다.",
};

export default function DocsPage() {
  return (
    <div className="min-h-screen bg-slate-900 text-slate-100">
      {/* Nav */}
      <nav className="border-b border-slate-800 px-6 py-4 flex items-center justify-between">
        <Link href="/" className="text-xl font-bold text-green-400">PRISM</Link>
        <div className="flex items-center gap-6 text-sm text-slate-400">
          <Link href="/docs/api" className="hover:text-slate-100 transition-colors">API 문서</Link>
          <Link href="/help" className="hover:text-slate-100 transition-colors">FAQ</Link>
          <Link href="/login" className="hover:text-slate-100 transition-colors">로그인</Link>
        </div>
      </nav>

      <div className="flex max-w-6xl mx-auto">
        {/* Sidebar */}
        <aside className="hidden md:block w-56 shrink-0 px-6 py-10 border-r border-slate-800 sticky top-0 h-screen overflow-y-auto">
          <div className="space-y-6 text-sm">
            {[
              {
                title: "시작하기",
                links: [
                  { label: "소개", href: "#intro" },
                  { label: "회원가입 & 로그인", href: "#auth" },
                  { label: "온보딩 투어", href: "#onboarding" },
                ],
              },
              {
                title: "전략",
                links: [
                  { label: "전략이란?", href: "#strategy-intro" },
                  { label: "UI 빌더로 만들기", href: "#strategy-ui" },
                  { label: "Python으로 만들기", href: "#strategy-python" },
                ],
              },
              {
                title: "백테스트",
                links: [
                  { label: "백테스트 실행", href: "#backtest-run" },
                  { label: "결과 해석", href: "#backtest-results" },
                  { label: "파라미터 최적화", href: "#optimization" },
                ],
              },
              {
                title: "모의 투자",
                links: [
                  { label: "세션 생성", href: "#paper-trading-start" },
                  { label: "포지션 관리", href: "#paper-trading-positions" },
                  { label: "알림 설정", href: "#paper-trading-alerts" },
                ],
              },
              {
                title: "기타",
                links: [
                  { label: "API 문서", href: "/docs/api" },
                  { label: "FAQ", href: "/help" },
                ],
              },
            ].map((section) => (
              <div key={section.title}>
                <div className="font-semibold text-slate-300 mb-2">{section.title}</div>
                <ul className="space-y-1">
                  {section.links.map((link) => (
                    <li key={link.label}>
                      <a
                        href={link.href}
                        className="text-slate-500 hover:text-slate-100 transition-colors block py-0.5"
                      >
                        {link.label}
                      </a>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </aside>

        {/* Content */}
        <main className="flex-1 px-8 py-10 max-w-3xl">
          {/* Intro */}
          <section id="intro" className="mb-14">
            <h1 className="text-4xl font-bold mb-4">사용자 가이드</h1>
            <p className="text-slate-400 leading-relaxed mb-4">
              PRISM은 한국 시장(KOSPI, KOSDAQ, 업비트)을 위한 전문 백테스트 플랫폼입니다.
              이 가이드는 전략 작성부터 백테스트 실행, 모의 투자까지 모든 기능을 단계별로 안내합니다.
            </p>
            <div className="flex gap-3">
              <Link href="/signup" className="px-4 py-2 bg-green-600 hover:bg-green-500 text-white rounded-lg text-sm font-semibold transition-colors">
                무료로 시작하기
              </Link>
              <Link href="/docs/api" className="px-4 py-2 bg-slate-700 hover:bg-slate-600 rounded-lg text-sm font-semibold transition-colors">
                API 문서 →
              </Link>
            </div>
          </section>

          <hr className="border-slate-800 mb-14" />

          {/* Auth */}
          <section id="auth" className="mb-14">
            <h2 className="text-2xl font-bold mb-4">회원가입 & 로그인</h2>
            <ol className="space-y-3 text-slate-300">
              <li className="flex gap-3">
                <span className="w-6 h-6 bg-green-700 rounded-full flex items-center justify-center text-white text-xs font-bold shrink-0 mt-0.5">1</span>
                <div>
                  <strong>/signup</strong> 페이지에서 이메일, 비밀번호, 이름을 입력하고 회원가입합니다.
                </div>
              </li>
              <li className="flex gap-3">
                <span className="w-6 h-6 bg-green-700 rounded-full flex items-center justify-center text-white text-xs font-bold shrink-0 mt-0.5">2</span>
                <div>회원가입 후 온보딩 가이드로 자동 이동합니다.</div>
              </li>
              <li className="flex gap-3">
                <span className="w-6 h-6 bg-green-700 rounded-full flex items-center justify-center text-white text-xs font-bold shrink-0 mt-0.5">3</span>
                <div>재방문 시 <strong>/login</strong> 페이지에서 로그인하면 대시보드로 이동합니다.</div>
              </li>
            </ol>
          </section>

          {/* Strategy */}
          <section id="strategy-intro" className="mb-10">
            <h2 className="text-2xl font-bold mb-4">전략이란?</h2>
            <p className="text-slate-400 leading-relaxed">
              전략(Strategy)은 <strong className="text-slate-200">언제 매수하고 언제 매도할지</strong>를 정의하는 규칙의 집합입니다.
              예를 들어 "5일 이동평균이 20일 이동평균을 상향 돌파하면 매수, 하향 돌파하면 매도"가 하나의 전략입니다.
            </p>
          </section>

          <section id="strategy-ui" className="mb-10">
            <h3 className="text-xl font-semibold mb-3">UI 빌더로 전략 만들기</h3>
            <p className="text-slate-400 leading-relaxed mb-3">
              코딩이 필요 없습니다. <strong className="text-slate-200">/strategies/new</strong> 페이지에서:
            </p>
            <ol className="space-y-2 text-sm text-slate-300 list-decimal list-inside">
              <li>지표 유형 선택 (이동평균, RSI, 볼린저 밴드 등)</li>
              <li>매수 조건 설정 (예: RSI &lt; 30이면 매수)</li>
              <li>매도 조건 설정 (예: RSI &gt; 70이면 매도)</li>
              <li>포지션 크기 및 손절/익절 설정</li>
              <li>저장 후 백테스트 실행</li>
            </ol>
          </section>

          <section id="strategy-python" className="mb-14">
            <h3 className="text-xl font-semibold mb-3">Python으로 전략 만들기</h3>
            <p className="text-slate-400 leading-relaxed mb-3">
              복잡한 전략은 Python으로 직접 구현할 수 있습니다. 기본 구조:
            </p>
            <div className="bg-slate-800 border border-slate-700 rounded-xl p-4 font-mono text-sm text-slate-300 overflow-x-auto">
              <pre>{`class MyStrategy:
    def __init__(self, short_window=5, long_window=20):
        self.short_window = short_window
        self.long_window = long_window

    def generate_signals(self, data):
        signals = []
        short_ma = data['close'].rolling(self.short_window).mean()
        long_ma = data['close'].rolling(self.long_window).mean()

        for i in range(1, len(data)):
            if short_ma[i] > long_ma[i] and short_ma[i-1] <= long_ma[i-1]:
                signals.append({'action': 'BUY', 'index': i})
            elif short_ma[i] < long_ma[i] and short_ma[i-1] >= long_ma[i-1]:
                signals.append({'action': 'SELL', 'index': i})

        return signals`}</pre>
            </div>
          </section>

          <hr className="border-slate-800 mb-14" />

          {/* Backtest */}
          <section id="backtest-run" className="mb-10">
            <h2 className="text-2xl font-bold mb-4">백테스트 실행</h2>
            <p className="text-slate-400 mb-4 leading-relaxed">
              <strong className="text-slate-200">/backtest</strong> 페이지에서 다음을 설정하고 실행하세요:
            </p>
            <div className="space-y-2 text-sm">
              {[
                { field: "전략", desc: "저장된 전략 중 하나를 선택" },
                { field: "종목", desc: "예: BTC/KRW, ETH/KRW, 삼성전자" },
                { field: "기간", desc: "시작일 ~ 종료일" },
                { field: "초기 자금", desc: "시뮬레이션 시작 자금 (예: ₩10,000,000)" },
                { field: "수수료율", desc: "실제 거래 수수료와 동일하게 설정 (예: 0.05%)" },
              ].map((row) => (
                <div key={row.field} className="flex gap-3 bg-slate-800 rounded-lg px-4 py-2.5 border border-slate-700">
                  <span className="text-green-400 font-semibold w-24 shrink-0">{row.field}</span>
                  <span className="text-slate-400">{row.desc}</span>
                </div>
              ))}
            </div>
          </section>

          <section id="backtest-results" className="mb-14">
            <h3 className="text-xl font-semibold mb-3">결과 해석</h3>
            <div className="space-y-2 text-sm">
              {[
                { metric: "누적 수익률", desc: "전체 기간 동안의 총 수익률. 양수면 수익, 음수면 손실." },
                { metric: "Sharpe Ratio", desc: "위험 대비 수익 비율. 1.0 이상이면 양호, 2.0 이상이면 우수." },
                { metric: "최대 낙폭 (MDD)", desc: "최고점 대비 최저점까지의 손실. 낮을수록 리스크 관리가 잘 된 전략." },
                { metric: "승률 (Win Rate)", desc: "전체 거래 중 수익 거래의 비율." },
                { metric: "손익비 (PnL Ratio)", desc: "평균 수익 / 평균 손실. 낮은 승률도 높은 손익비로 보완 가능." },
              ].map((row) => (
                <div key={row.metric} className="bg-slate-800 rounded-lg px-4 py-3 border border-slate-700">
                  <div className="text-green-400 font-semibold text-sm">{row.metric}</div>
                  <div className="text-slate-400 text-sm mt-0.5">{row.desc}</div>
                </div>
              ))}
            </div>
          </section>

          <hr className="border-slate-800 mb-14" />

          {/* Paper Trading */}
          <section id="paper-trading-start" className="mb-10">
            <h2 className="text-2xl font-bold mb-4">모의 투자 (Paper Trading)</h2>
            <p className="text-slate-400 leading-relaxed mb-4">
              모의 투자는 실시간 시장 데이터를 사용하여 가상 자금으로 전략을 검증하는 기능입니다.
            </p>
            <ol className="space-y-2 text-sm text-slate-300 list-decimal list-inside">
              <li><strong>/paper-trading</strong> 페이지에서 "새 세션 만들기" 클릭</li>
              <li>전략, 초기 자금, 종목 선택</li>
              <li>세션 시작 — 실시간으로 포지션 및 수익 추적</li>
              <li>세션 종료 후 백테스트 결과와 비교 분석</li>
            </ol>
          </section>

          <section id="paper-trading-alerts" className="mb-14">
            <h3 className="text-xl font-semibold mb-3">알림 설정</h3>
            <p className="text-slate-400 text-sm leading-relaxed">
              포지션 손익이 설정한 임계값에 도달하면 대시보드 알림을 받을 수 있습니다.
              예: "손실이 -5% 초과 시 알림", "수익이 +10% 달성 시 알림".
            </p>
          </section>

          {/* Next */}
          <div className="bg-slate-800 rounded-2xl border border-slate-700 p-6 flex flex-col sm:flex-row gap-4 items-start sm:items-center justify-between">
            <div>
              <div className="font-semibold mb-1">개발자이신가요?</div>
              <div className="text-slate-400 text-sm">REST API로 PRISM을 외부 시스템과 연동하세요.</div>
            </div>
            <Link
              href="/docs/api"
              className="px-5 py-2.5 bg-green-600 hover:bg-green-500 text-white rounded-lg text-sm font-semibold transition-colors shrink-0"
            >
              API 문서 →
            </Link>
          </div>
        </main>
      </div>
    </div>
  );
}
