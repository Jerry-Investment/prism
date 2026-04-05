"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import AuthGuard from "@/components/AuthGuard";
import { useAuthStore } from "@/lib/authStore";

const STEPS = [
  {
    id: 1,
    title: "PRISM에 오신 것을 환영합니다!",
    content: (
      <div className="space-y-4">
        <p className="text-slate-300 leading-relaxed">
          PRISM은 <strong className="text-green-400">한국 시장 특화 백테스트 플랫폼</strong>입니다.
          KOSPI, KOSDAQ, 업비트 암호화폐 데이터를 기반으로 투자 전략을 검증하고 최적화할 수 있습니다.
        </p>
        <div className="grid grid-cols-2 gap-3 mt-6">
          {[
            { icon: "📈", label: "백테스트", desc: "과거 데이터로 전략 검증" },
            { icon: "🔬", label: "전략 최적화", desc: "최적 파라미터 자동 탐색" },
            { icon: "📊", label: "리스크 분석", desc: "Sharpe, MDD 등 지표" },
            { icon: "🤖", label: "모의 투자", desc: "실시간 Paper Trading" },
          ].map((item) => (
            <div key={item.label} className="bg-slate-700/50 rounded-lg p-3 flex items-start gap-3">
              <span className="text-2xl">{item.icon}</span>
              <div>
                <div className="font-semibold text-sm">{item.label}</div>
                <div className="text-slate-400 text-xs">{item.desc}</div>
              </div>
            </div>
          ))}
        </div>
      </div>
    ),
  },
  {
    id: 2,
    title: "전략 만들기",
    content: (
      <div className="space-y-4">
        <p className="text-slate-300 leading-relaxed">
          <strong className="text-green-400">전략(Strategy)</strong>은 언제 매수·매도할지를 정의하는 규칙입니다.
          PRISM에서는 두 가지 방법으로 전략을 만들 수 있습니다.
        </p>
        <div className="space-y-3">
          <div className="bg-slate-700/50 rounded-lg p-4 border border-slate-600">
            <div className="font-semibold mb-1">1. UI 빌더 (초보자 추천)</div>
            <p className="text-slate-400 text-sm">
              이동평균, RSI, 볼린저 밴드 등 기본 지표를 선택하고 파라미터를 설정하면 전략이 완성됩니다.
              코딩 지식이 없어도 됩니다.
            </p>
          </div>
          <div className="bg-slate-700/50 rounded-lg p-4 border border-slate-600">
            <div className="font-semibold mb-1">2. Python 코드 (고급)</div>
            <p className="text-slate-400 text-sm">
              직접 Python으로 전략 로직을 작성하세요. 복잡한 신호 조합, 커스텀 지표, 포지션 관리까지
              자유롭게 구현할 수 있습니다.
            </p>
          </div>
        </div>
        <div className="bg-green-900/30 border border-green-700/50 rounded-lg p-3 text-sm text-green-300">
          💡 팁: 전략 페이지에서 &quot;샘플 전략&quot;을 불러와 바로 백테스트를 실행해보세요!
        </div>
      </div>
    ),
  },
  {
    id: 3,
    title: "첫 백테스트 실행하기",
    content: (
      <div className="space-y-4">
        <p className="text-slate-300 leading-relaxed">
          백테스트는 3단계로 실행됩니다.
        </p>
        <ol className="space-y-3">
          {[
            {
              step: "1",
              title: "전략 선택",
              desc: "저장된 전략을 선택하거나 새로 만드세요.",
            },
            {
              step: "2",
              title: "기간 및 종목 설정",
              desc: "백테스트할 종목(예: BTC/KRW)과 기간(예: 2024-01-01 ~ 2024-12-31)을 설정하세요.",
            },
            {
              step: "3",
              title: "결과 분석",
              desc: "수익률 곡선, Sharpe Ratio, 최대 낙폭(MDD), 거래 내역을 확인하세요.",
            },
          ].map((item) => (
            <div key={item.step} className="flex gap-4 bg-slate-700/50 rounded-lg p-4">
              <div className="w-8 h-8 bg-green-600 rounded-full flex items-center justify-center text-white font-bold text-sm flex-shrink-0">
                {item.step}
              </div>
              <div>
                <div className="font-semibold text-sm">{item.title}</div>
                <div className="text-slate-400 text-sm mt-0.5">{item.desc}</div>
              </div>
            </div>
          ))}
        </ol>
        <div className="bg-green-900/30 border border-green-700/50 rounded-lg p-3 text-sm text-green-300">
          💡 팁: 백테스트 페이지에서 &quot;샘플로 실행하기&quot;를 클릭하면 설정 없이 바로 체험할 수 있습니다!
        </div>
      </div>
    ),
  },
  {
    id: 4,
    title: "모의 투자 시작하기",
    content: (
      <div className="space-y-4">
        <p className="text-slate-300 leading-relaxed">
          <strong className="text-green-400">모의 투자(Paper Trading)</strong>는 실제 돈을 쓰지 않고
          실시간 시장 데이터로 전략을 테스트하는 방법입니다.
        </p>
        <div className="space-y-3">
          <div className="bg-slate-700/50 rounded-lg p-4">
            <div className="font-semibold mb-1 text-sm">지원 시장</div>
            <div className="flex gap-2 flex-wrap">
              {["Upbit BTC/KRW", "Upbit ETH/KRW", "기타 업비트 상장 코인"].map((m) => (
                <span key={m} className="px-2 py-1 bg-slate-600 rounded text-xs">{m}</span>
              ))}
            </div>
          </div>
          <div className="bg-slate-700/50 rounded-lg p-4">
            <div className="font-semibold mb-1 text-sm">주요 기능</div>
            <ul className="text-slate-400 text-sm space-y-1">
              <li>• 실시간 포지션 및 수익/손실 추적</li>
              <li>• 주문 체결 내역 및 거래 로그</li>
              <li>• 리스크 알림 설정 (손절 임박 등)</li>
              <li>• 백테스트 결과와 실전 성과 비교</li>
            </ul>
          </div>
        </div>
      </div>
    ),
  },
  {
    id: 5,
    title: "준비 완료!",
    content: (
      <div className="space-y-4 text-center">
        <div className="text-6xl mb-4">🎉</div>
        <p className="text-slate-300 leading-relaxed">
          PRISM 사용 준비가 완료되었습니다!<br />
          아래 바로가기로 원하는 기능을 시작하세요.
        </p>
        <div className="grid grid-cols-2 gap-3 mt-6 text-left">
          {[
            { label: "전략 만들기", href: "/strategies", icon: "🎯", desc: "새 전략을 등록하세요" },
            { label: "백테스트 실행", href: "/backtest", icon: "📈", desc: "전략을 검증하세요" },
            { label: "모의 투자", href: "/paper-trading", icon: "🤖", desc: "실시간 테스트" },
            { label: "도움말", href: "/help", icon: "❓", desc: "FAQ 및 가이드" },
          ].map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className="bg-slate-700/50 hover:bg-slate-700 border border-slate-600 rounded-lg p-4 transition-colors flex items-start gap-3"
            >
              <span className="text-2xl">{item.icon}</span>
              <div>
                <div className="font-semibold text-sm">{item.label}</div>
                <div className="text-slate-400 text-xs">{item.desc}</div>
              </div>
            </Link>
          ))}
        </div>
      </div>
    ),
  },
];

export default function OnboardingPage() {
  const [step, setStep] = useState(0);
  const router = useRouter();
  const user = useAuthStore((s) => s.user);

  const current = STEPS[step];
  const isLast = step === STEPS.length - 1;

  function handleNext() {
    if (isLast) {
      router.push("/dashboard");
    } else {
      setStep((s) => s + 1);
    }
  }

  return (
    <AuthGuard>
      <div className="min-h-screen flex items-center justify-center p-6">
        <div className="w-full max-w-lg">
          {/* Progress */}
          <div className="flex gap-1.5 mb-8">
            {STEPS.map((s, i) => (
              <div
                key={s.id}
                className={`h-1.5 flex-1 rounded-full transition-colors ${
                  i <= step ? "bg-green-500" : "bg-slate-700"
                }`}
              />
            ))}
          </div>

          {/* Card */}
          <div className="bg-slate-800 rounded-2xl border border-slate-700 p-8">
            <div className="text-xs text-slate-500 mb-2">
              {step + 1} / {STEPS.length}
            </div>
            <h1 className="text-2xl font-bold mb-6">
              {step === 0 && user?.full_name
                ? `${user.full_name}님, ${current.title}`
                : current.title}
            </h1>
            <div>{current.content}</div>
          </div>

          {/* Actions */}
          <div className="flex items-center justify-between mt-6">
            <button
              onClick={() => setStep((s) => Math.max(0, s - 1))}
              disabled={step === 0}
              className="text-sm text-slate-400 hover:text-slate-200 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
            >
              ← 이전
            </button>
            <div className="flex gap-3">
              <Link
                href="/dashboard"
                className="text-sm text-slate-500 hover:text-slate-300 transition-colors"
              >
                건너뛰기
              </Link>
              <button
                onClick={handleNext}
                className="px-6 py-2 bg-green-600 hover:bg-green-500 text-white font-semibold rounded-lg transition-colors text-sm"
              >
                {isLast ? "대시보드로 이동 →" : "다음 →"}
              </button>
            </div>
          </div>
        </div>
      </div>
    </AuthGuard>
  );
}
