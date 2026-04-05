import Link from "next/link";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "도움말 / FAQ — PRISM",
  description: "PRISM 사용 중 자주 묻는 질문과 답변을 확인하세요.",
};

const FAQ_SECTIONS = [
  {
    section: "시작하기",
    items: [
      {
        q: "PRISM은 어떤 서비스인가요?",
        a: "PRISM(Portfolio Research & Investment Simulation Machine)은 한국 시장(KOSPI, KOSDAQ, 업비트)에 특화된 전문 백테스트 및 모의 투자 플랫폼입니다. 투자 전략을 과거 데이터로 검증하고, 실시간 모의 투자로 실전 준비를 할 수 있습니다.",
      },
      {
        q: "회원가입 없이도 이용할 수 있나요?",
        a: "현재 모든 기능은 로그인이 필요합니다. 무료 계정을 만들면 즉시 백테스트를 시작할 수 있으며, 신용카드 등 결제 정보가 필요하지 않습니다.",
      },
      {
        q: "처음에 무엇부터 시작해야 하나요?",
        a: "회원가입 후 온보딩 가이드를 따라가면 5분 안에 첫 백테스트를 실행할 수 있습니다. 전략 페이지에서 샘플 전략을 불러와 바로 백테스트해보세요.",
      },
    ],
  },
  {
    section: "백테스트",
    items: [
      {
        q: "백테스트란 무엇인가요?",
        a: "백테스트는 과거 시장 데이터를 사용하여 투자 전략이 특정 기간에 어떤 성과를 냈을지 시뮬레이션하는 방법입니다. 실제 돈을 투자하기 전에 전략의 유효성을 검증하는 데 사용합니다.",
      },
      {
        q: "어떤 데이터를 사용하나요?",
        a: "무료 플랜은 일봉 기준 1년 데이터를 제공합니다. Pro 플랜은 분봉 포함 5년 이상의 데이터를 지원합니다. 지원 시장: KOSPI·KOSDAQ 주식, 업비트 암호화폐(BTC, ETH 등).",
      },
      {
        q: "슬리피지와 수수료가 반영되나요?",
        a: "네. 백테스트 설정에서 거래 수수료율과 슬리피지(체결 가격 오차)를 직접 입력할 수 있습니다. 현실에 가까운 시뮬레이션을 위해 반드시 설정하는 것을 권장합니다.",
      },
      {
        q: "백테스트 결과는 어떻게 해석하나요?",
        a: "주요 지표: 누적 수익률(총 성과), Sharpe Ratio(위험 대비 수익, 높을수록 좋음), 최대 낙폭 MDD(최악의 손실 구간), Win Rate(승률). 자세한 설명은 사용자 가이드를 참조하세요.",
      },
    ],
  },
  {
    section: "전략 작성",
    items: [
      {
        q: "프로그래밍을 모르면 전략을 만들 수 없나요?",
        a: "아닙니다. UI 빌더를 사용하면 코딩 없이 이동평균 교차, RSI 과매수/과매도, 볼린저 밴드 등 기본 전략을 만들 수 있습니다. Python을 알면 더 복잡한 전략도 구현할 수 있습니다.",
      },
      {
        q: "전략을 공유할 수 있나요?",
        a: "팀 플랜 사용자는 팀원과 전략을 공유하고 공동 편집할 수 있습니다. 무료·Pro 플랜에서는 개인 전략만 관리할 수 있습니다.",
      },
    ],
  },
  {
    section: "모의 투자 (Paper Trading)",
    items: [
      {
        q: "모의 투자는 실제 돈이 필요한가요?",
        a: "아닙니다. 모의 투자는 가상 자금으로 실시간 시장 가격을 사용하는 시뮬레이션입니다. 실제 거래소 계정이나 입금이 전혀 필요하지 않습니다.",
      },
      {
        q: "어떤 시장을 지원하나요?",
        a: "현재 업비트 암호화폐 시장(BTC/KRW, ETH/KRW 등)을 지원합니다. KOSPI/KOSDAQ 모의 투자는 추후 지원 예정입니다.",
      },
      {
        q: "모의 투자 세션을 여러 개 만들 수 있나요?",
        a: "Pro 플랜부터 다수의 모의 투자 세션을 동시에 운영할 수 있습니다. 무료 플랜은 1개 세션으로 제한됩니다.",
      },
    ],
  },
  {
    section: "계정 및 데이터",
    items: [
      {
        q: "비밀번호를 잊어버렸어요.",
        a: "로그인 페이지의 '비밀번호 찾기' 링크를 통해 이메일로 재설정 링크를 받을 수 있습니다.",
      },
      {
        q: "계정을 삭제하고 싶습니다.",
        a: "계정 설정 페이지에서 계정 삭제를 요청할 수 있습니다. 삭제 시 모든 데이터(전략, 백테스트 결과, 모의 투자 기록)가 영구적으로 삭제됩니다.",
      },
      {
        q: "내 데이터는 어떻게 보호되나요?",
        a: "모든 데이터는 전송 중 TLS로 암호화되며, 저장 시 AES-256으로 암호화됩니다. 개인정보처리방침에서 상세 내용을 확인하세요.",
      },
    ],
  },
];

export default function HelpPage() {
  return (
    <div className="min-h-screen bg-slate-900 text-slate-100">
      {/* Nav */}
      <nav className="border-b border-slate-800 px-6 py-4 flex items-center justify-between">
        <Link href="/" className="text-xl font-bold text-green-400">PRISM</Link>
        <div className="flex items-center gap-6 text-sm text-slate-400">
          <Link href="/docs" className="hover:text-slate-100 transition-colors">문서</Link>
          <Link href="/login" className="hover:text-slate-100 transition-colors">로그인</Link>
          <Link href="/signup" className="px-4 py-1.5 bg-green-600 hover:bg-green-500 text-white rounded-lg transition-colors">
            무료 시작
          </Link>
        </div>
      </nav>

      <div className="max-w-3xl mx-auto px-6 py-16">
        <div className="text-center mb-14">
          <h1 className="text-4xl font-bold mb-3">도움말 / FAQ</h1>
          <p className="text-slate-400">PRISM 사용 중 궁금한 점을 찾아보세요</p>
        </div>

        {/* Quick links */}
        <div className="flex flex-wrap gap-2 mb-12 justify-center">
          {FAQ_SECTIONS.map((s) => (
            <a
              key={s.section}
              href={`#${s.section}`}
              className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 border border-slate-700 rounded-lg text-sm text-slate-300 transition-colors"
            >
              {s.section}
            </a>
          ))}
        </div>

        {/* FAQ Sections */}
        <div className="space-y-12">
          {FAQ_SECTIONS.map((section) => (
            <div key={section.section} id={section.section}>
              <h2 className="text-xl font-bold mb-4 text-green-400">{section.section}</h2>
              <div className="space-y-3">
                {section.items.map((item) => (
                  <div key={item.q} className="bg-slate-800 rounded-xl border border-slate-700 p-5">
                    <h3 className="font-semibold mb-2">{item.q}</h3>
                    <p className="text-slate-400 text-sm leading-relaxed">{item.a}</p>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>

        {/* Contact */}
        <div className="mt-16 text-center bg-slate-800 rounded-2xl border border-slate-700 p-8">
          <h2 className="text-xl font-bold mb-2">찾는 답변이 없나요?</h2>
          <p className="text-slate-400 mb-4 text-sm">
            문서를 확인하거나 이메일로 문의해주세요.
          </p>
          <div className="flex gap-3 justify-center">
            <Link
              href="/docs"
              className="px-5 py-2 bg-slate-700 hover:bg-slate-600 rounded-lg text-sm font-semibold transition-colors"
            >
              사용자 가이드 →
            </Link>
            <a
              href="mailto:support@prism.kr"
              className="px-5 py-2 bg-green-600 hover:bg-green-500 text-white rounded-lg text-sm font-semibold transition-colors"
            >
              이메일 문의
            </a>
          </div>
        </div>
      </div>

      {/* Footer */}
      <footer className="border-t border-slate-800 px-6 py-6 text-center text-xs text-slate-600">
        <Link href="/" className="hover:text-slate-400 transition-colors">홈</Link>
        {" · "}
        <Link href="/docs" className="hover:text-slate-400 transition-colors">문서</Link>
        {" · "}
        <Link href="/legal/terms" className="hover:text-slate-400 transition-colors">이용약관</Link>
        {" · "}
        <Link href="/legal/privacy" className="hover:text-slate-400 transition-colors">개인정보처리방침</Link>
      </footer>
    </div>
  );
}
