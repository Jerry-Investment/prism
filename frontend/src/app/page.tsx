import Link from "next/link";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "PRISM — 한국 시장 백테스트 플랫폼",
  description: "PRISM은 KOSPI, KOSDAQ, 암호화폐 시장을 위한 전문 백테스트 및 모의 투자 플랫폼입니다. 나만의 전략을 검증하고 최적화하세요.",
  keywords: "백테스트, 퀀트, 주식, 암호화폐, 전략, KOSPI, KOSDAQ, 업비트",
  openGraph: {
    title: "PRISM — 한국 시장 백테스트 플랫폼",
    description: "전문 백테스트 플랫폼으로 당신의 투자 전략을 검증하세요.",
    type: "website",
  },
};

const FEATURES = [
  {
    icon: "📈",
    title: "이벤트 기반 백테스트",
    desc: "실제 시장 미시구조를 반영한 정확한 시뮬레이션. 슬리피지·수수료 포함 현실적인 성과 측정.",
  },
  {
    icon: "🔬",
    title: "전략 최적화",
    desc: "파라미터 그리드 서치 및 Walk-Forward 검증으로 과적합 없는 최적 파라미터를 자동 탐색.",
  },
  {
    icon: "📊",
    title: "위험 분석",
    desc: "Sharpe Ratio, Max Drawdown, VaR, 전략 비교 등 프로급 리스크 지표를 한눈에 확인.",
  },
  {
    icon: "🤖",
    title: "모의 투자 (Paper Trading)",
    desc: "실시간 Upbit 시장 데이터로 자금 위험 없이 전략을 실전 검증. 포지션·수익·로그 완전 추적.",
  },
  {
    icon: "🇰🇷",
    title: "한국 시장 특화",
    desc: "KOSPI, KOSDAQ, 업비트 암호화폐 데이터 완전 지원. 한국 거래 시간·공휴일 자동 반영.",
  },
  {
    icon: "⚡",
    title: "빠른 REST API",
    desc: "OpenAPI 기반 REST API로 외부 시스템과 손쉽게 연동. 자동화 트레이딩 파이프라인 구축 가능.",
  },
];

const PRICING = [
  {
    name: "무료",
    price: "₩0",
    period: "/월",
    highlight: false,
    features: [
      "백테스트 월 50회",
      "전략 저장 5개",
      "데이터 1년 (일봉)",
      "기본 리스크 지표",
      "커뮤니티 지원",
    ],
    cta: "무료로 시작",
    href: "/signup",
  },
  {
    name: "Pro",
    price: "₩29,900",
    period: "/월",
    highlight: true,
    features: [
      "백테스트 무제한",
      "전략 저장 무제한",
      "데이터 5년 (분봉 포함)",
      "파라미터 최적화",
      "모의 투자 (Paper Trading)",
      "우선 기술 지원",
    ],
    cta: "Pro 시작하기",
    href: "/signup?plan=pro",
  },
  {
    name: "팀",
    price: "₩79,900",
    period: "/월",
    highlight: false,
    features: [
      "Pro 기능 전체 포함",
      "팀원 5명",
      "전략 공유 및 협업",
      "API 키 관리",
      "전용 기술 지원",
      "맞춤 온보딩",
    ],
    cta: "팀 플랜 문의",
    href: "mailto:hello@prism.kr",
  },
];

const FAQ = [
  {
    q: "백테스트란 무엇인가요?",
    a: "백테스트는 과거 시장 데이터를 사용하여 투자 전략을 시뮬레이션하는 방법입니다. 실제 자금을 투자하기 전에 전략의 성과를 검증할 수 있습니다.",
  },
  {
    q: "어떤 시장 데이터를 지원하나요?",
    a: "KOSPI, KOSDAQ 주식 데이터(일봉/분봉)와 업비트 암호화폐 데이터(BTC, ETH 등 주요 코인)를 지원합니다. Pro 플랜에서는 5년 이상의 데이터를 이용할 수 있습니다.",
  },
  {
    q: "모의 투자(Paper Trading)는 어떻게 작동하나요?",
    a: "실시간 업비트 API와 연동하여 실제 가격으로 가상 거래를 실행합니다. 실제 자금 손실 없이 전략을 실전과 동일한 조건으로 검증할 수 있습니다.",
  },
  {
    q: "프로그래밍 지식이 없어도 사용할 수 있나요?",
    a: "네. 기본 전략(이동평균, RSI, 볼린저 밴드 등)은 UI에서 파라미터만 설정하면 바로 백테스트할 수 있습니다. 고급 전략은 Python 코드로 작성할 수 있습니다.",
  },
  {
    q: "데이터는 안전하게 보관되나요?",
    a: "모든 데이터는 암호화되어 저장되며, 제3자와 공유하지 않습니다. 언제든지 계정 삭제 및 데이터 완전 삭제를 요청할 수 있습니다.",
  },
];

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-slate-900 text-slate-100">
      {/* Nav */}
      <nav className="border-b border-slate-800 px-6 py-4 flex items-center justify-between">
        <span className="text-xl font-bold text-green-400">PRISM</span>
        <div className="flex items-center gap-6 text-sm text-slate-400">
          <Link href="/docs" className="hover:text-slate-100 transition-colors">문서</Link>
          <Link href="/help" className="hover:text-slate-100 transition-colors">도움말</Link>
          <Link href="/login" className="hover:text-slate-100 transition-colors">로그인</Link>
          <Link
            href="/signup"
            className="px-4 py-1.5 bg-green-600 hover:bg-green-500 text-white rounded-lg transition-colors"
          >
            무료 시작
          </Link>
        </div>
      </nav>

      {/* Hero */}
      <section className="px-6 py-24 text-center max-w-4xl mx-auto">
        <div className="inline-block px-3 py-1 bg-green-900/40 border border-green-700/50 text-green-400 text-xs rounded-full mb-6">
          한국 시장 특화 백테스트 플랫폼
        </div>
        <h1 className="text-5xl md:text-6xl font-bold mb-6 leading-tight">
          투자 전략을<br />
          <span className="text-green-400">데이터로 검증</span>하세요
        </h1>
        <p className="text-slate-400 text-xl mb-10 max-w-2xl mx-auto">
          PRISM은 KOSPI·KOSDAQ·암호화폐를 위한 전문 백테스트 플랫폼입니다.
          아이디어를 코드로 구현하고, 과거 데이터로 검증하고, 모의 투자로 실전 준비하세요.
        </p>
        <div className="flex flex-col sm:flex-row gap-4 justify-center">
          <Link
            href="/signup"
            className="px-8 py-4 bg-green-600 hover:bg-green-500 text-white font-semibold rounded-xl text-lg transition-colors"
          >
            무료로 시작하기
          </Link>
          <Link
            href="/docs"
            className="px-8 py-4 bg-slate-800 hover:bg-slate-700 border border-slate-600 text-slate-100 font-semibold rounded-xl text-lg transition-colors"
          >
            문서 보기
          </Link>
        </div>
        <p className="text-slate-500 text-sm mt-6">신용카드 불필요 · 무료 플랜 영구 제공</p>
      </section>

      {/* Features */}
      <section className="px-6 py-20 max-w-6xl mx-auto">
        <div className="text-center mb-14">
          <h2 className="text-3xl font-bold mb-3">왜 PRISM인가요?</h2>
          <p className="text-slate-400">퀀트 트레이더를 위한 모든 도구</p>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {FEATURES.map((f) => (
            <div key={f.title} className="bg-slate-800 rounded-xl border border-slate-700 p-6">
              <div className="text-3xl mb-4">{f.icon}</div>
              <h3 className="text-lg font-semibold mb-2">{f.title}</h3>
              <p className="text-slate-400 text-sm leading-relaxed">{f.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Pricing */}
      <section id="pricing" className="px-6 py-20 bg-slate-800/30">
        <div className="max-w-5xl mx-auto">
          <div className="text-center mb-14">
            <h2 className="text-3xl font-bold mb-3">요금제</h2>
            <p className="text-slate-400">팀 규모와 목적에 맞는 플랜을 선택하세요</p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {PRICING.map((plan) => (
              <div
                key={plan.name}
                className={`rounded-xl border p-6 flex flex-col ${
                  plan.highlight
                    ? "bg-green-950/40 border-green-600"
                    : "bg-slate-800 border-slate-700"
                }`}
              >
                {plan.highlight && (
                  <div className="text-xs text-green-400 font-semibold mb-3 uppercase tracking-wider">
                    인기
                  </div>
                )}
                <h3 className="text-xl font-bold mb-1">{plan.name}</h3>
                <div className="flex items-baseline gap-1 mb-6">
                  <span className="text-3xl font-bold">{plan.price}</span>
                  <span className="text-slate-400 text-sm">{plan.period}</span>
                </div>
                <ul className="space-y-2 mb-8 flex-1">
                  {plan.features.map((feat) => (
                    <li key={feat} className="flex items-start gap-2 text-sm text-slate-300">
                      <span className="text-green-400 mt-0.5">✓</span>
                      {feat}
                    </li>
                  ))}
                </ul>
                <Link
                  href={plan.href}
                  className={`block text-center py-3 rounded-lg font-semibold transition-colors ${
                    plan.highlight
                      ? "bg-green-600 hover:bg-green-500 text-white"
                      : "bg-slate-700 hover:bg-slate-600 text-slate-100"
                  }`}
                >
                  {plan.cta}
                </Link>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* FAQ */}
      <section className="px-6 py-20 max-w-3xl mx-auto">
        <div className="text-center mb-14">
          <h2 className="text-3xl font-bold mb-3">자주 묻는 질문</h2>
        </div>
        <div className="space-y-4">
          {FAQ.map((item) => (
            <div key={item.q} className="bg-slate-800 rounded-xl border border-slate-700 p-6">
              <h3 className="font-semibold mb-2">{item.q}</h3>
              <p className="text-slate-400 text-sm leading-relaxed">{item.a}</p>
            </div>
          ))}
        </div>
        <div className="text-center mt-8">
          <Link href="/help" className="text-green-400 hover:text-green-300 text-sm">
            더 많은 질문 보기 →
          </Link>
        </div>
      </section>

      {/* CTA */}
      <section className="px-6 py-20 text-center">
        <div className="max-w-2xl mx-auto bg-green-950/40 border border-green-700/50 rounded-2xl p-12">
          <h2 className="text-3xl font-bold mb-4">지금 바로 시작하세요</h2>
          <p className="text-slate-400 mb-8">
            무료 계정으로 백테스트를 경험해보세요. 신용카드가 필요하지 않습니다.
          </p>
          <Link
            href="/signup"
            className="inline-block px-10 py-4 bg-green-600 hover:bg-green-500 text-white font-semibold rounded-xl text-lg transition-colors"
          >
            무료 계정 만들기
          </Link>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-slate-800 px-6 py-10">
        <div className="max-w-6xl mx-auto grid grid-cols-2 md:grid-cols-4 gap-8 text-sm text-slate-400">
          <div>
            <div className="text-green-400 font-bold text-base mb-3">PRISM</div>
            <p className="text-xs leading-relaxed">
              Portfolio Research &amp;<br />Investment Simulation Machine
            </p>
          </div>
          <div>
            <div className="font-semibold text-slate-300 mb-3">제품</div>
            <ul className="space-y-2">
              <li><Link href="/signup" className="hover:text-slate-100 transition-colors">회원가입</Link></li>
              <li><Link href="/login" className="hover:text-slate-100 transition-colors">로그인</Link></li>
              <li><Link href="#pricing" className="hover:text-slate-100 transition-colors">요금제</Link></li>
            </ul>
          </div>
          <div>
            <div className="font-semibold text-slate-300 mb-3">리소스</div>
            <ul className="space-y-2">
              <li><Link href="/docs" className="hover:text-slate-100 transition-colors">사용자 가이드</Link></li>
              <li><Link href="/docs/api" className="hover:text-slate-100 transition-colors">API 문서</Link></li>
              <li><Link href="/help" className="hover:text-slate-100 transition-colors">도움말 / FAQ</Link></li>
            </ul>
          </div>
          <div>
            <div className="font-semibold text-slate-300 mb-3">법적 고지</div>
            <ul className="space-y-2">
              <li><Link href="/legal/terms" className="hover:text-slate-100 transition-colors">이용약관</Link></li>
              <li><Link href="/legal/privacy" className="hover:text-slate-100 transition-colors">개인정보처리방침</Link></li>
            </ul>
          </div>
        </div>
        <div className="max-w-6xl mx-auto mt-8 pt-6 border-t border-slate-800 text-center text-xs text-slate-600">
          © 2026 PRISM. All rights reserved. 본 서비스는 투자 조언을 제공하지 않습니다.
        </div>
      </footer>
    </div>
  );
}
