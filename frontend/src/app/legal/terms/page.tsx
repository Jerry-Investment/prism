import Link from "next/link";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "이용약관 — PRISM",
  description: "PRISM 서비스 이용약관",
};

export default function TermsPage() {
  return (
    <div className="min-h-screen bg-slate-900 text-slate-100">
      <nav className="border-b border-slate-800 px-6 py-4 flex items-center justify-between">
        <Link href="/" className="text-xl font-bold text-green-400">PRISM</Link>
        <div className="flex items-center gap-4 text-sm text-slate-400">
          <Link href="/legal/privacy" className="hover:text-slate-100 transition-colors">개인정보처리방침</Link>
          <Link href="/login" className="hover:text-slate-100 transition-colors">로그인</Link>
        </div>
      </nav>

      <div className="max-w-3xl mx-auto px-6 py-16">
        <h1 className="text-3xl font-bold mb-2">이용약관</h1>
        <p className="text-slate-500 text-sm mb-10">시행일: 2026년 1월 1일</p>

        <div className="prose prose-slate max-w-none space-y-8 text-slate-300 text-sm leading-relaxed">

          <section>
            <h2 className="text-lg font-semibold text-slate-100 mb-3">제1조 (목적)</h2>
            <p>
              이 약관은 PRISM(이하 &quot;회사&quot;)이 제공하는 백테스트 및 모의 투자 서비스(이하 &quot;서비스&quot;)의 이용 조건과 절차, 이용자와 회사의 권리·의무 및 책임사항을 규정함을 목적으로 합니다.
            </p>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-slate-100 mb-3">제2조 (정의)</h2>
            <ul className="space-y-2 list-disc list-inside text-slate-400">
              <li><strong className="text-slate-300">서비스</strong>: 회사가 제공하는 백테스트, 전략 관리, 모의 투자, API 등 모든 기능을 의미합니다.</li>
              <li><strong className="text-slate-300">이용자</strong>: 이 약관에 동의하고 서비스를 이용하는 모든 회원 및 비회원을 의미합니다.</li>
              <li><strong className="text-slate-300">회원</strong>: 회사에 개인정보를 제공하여 회원가입을 완료한 자를 의미합니다.</li>
            </ul>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-slate-100 mb-3">제3조 (약관의 효력 및 변경)</h2>
            <p className="text-slate-400">
              이 약관은 서비스 화면에 게시하거나 이메일로 통지함으로써 효력이 발생합니다. 회사는 관계 법령을 위반하지 않는 범위에서 약관을 변경할 수 있으며, 변경된 약관은 시행일 7일 전에 공지합니다.
            </p>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-slate-100 mb-3">제4조 (회원가입)</h2>
            <ol className="space-y-2 list-decimal list-inside text-slate-400">
              <li>이용자는 회사가 정한 양식에 따라 이용 신청을 하여야 합니다.</li>
              <li>회사는 다음에 해당하는 신청에 대해 승낙을 거부하거나 사후에 이용계약을 해지할 수 있습니다: 타인의 명의를 도용한 경우, 허위 정보를 기재한 경우, 기타 법령 위반 또는 회사 정책에 반하는 경우.</li>
            </ol>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-slate-100 mb-3">제5조 (서비스 이용)</h2>
            <p className="text-slate-400 mb-2">서비스는 연중무휴, 24시간 제공을 원칙으로 합니다. 단, 다음의 경우 서비스 제공이 중단될 수 있습니다:</p>
            <ul className="list-disc list-inside text-slate-400 space-y-1">
              <li>시스템 점검, 교체 등 회사의 필요에 의한 경우</li>
              <li>천재지변, 국가 비상사태 등 불가항력적 사유가 있는 경우</li>
              <li>외부 API 제공업체(업비트, KIS 등)의 장애로 인한 경우</li>
            </ul>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-slate-100 mb-3">제6조 (투자 고지)</h2>
            <div className="bg-yellow-900/30 border border-yellow-700/50 rounded-xl p-4 text-yellow-300">
              <strong>중요 고지:</strong> PRISM은 투자 참고 도구로만 사용해야 하며, 투자 조언이나 추천을 제공하지 않습니다. 모든 투자 결정과 그에 따른 손실은 이용자 본인의 책임입니다. 과거 백테스트 결과가 미래 수익을 보장하지 않습니다.
            </div>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-slate-100 mb-3">제7조 (이용자의 의무)</h2>
            <ul className="list-disc list-inside text-slate-400 space-y-1">
              <li>타인의 계정을 무단으로 사용하지 않습니다.</li>
              <li>서비스를 통해 취득한 정보를 회사의 사전 동의 없이 상업적 목적으로 사용하지 않습니다.</li>
              <li>서비스 운영을 방해하거나 보안을 위협하는 행위를 하지 않습니다.</li>
              <li>법령 및 이 약관이 금지하는 행위를 하지 않습니다.</li>
            </ul>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-slate-100 mb-3">제8조 (서비스 이용 제한)</h2>
            <p className="text-slate-400">
              이용자가 이 약관의 의무를 위반하거나 서비스의 정상적인 운영을 방해한 경우, 회사는 사전 통지 없이 서비스 이용을 제한 또는 중지할 수 있습니다.
            </p>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-slate-100 mb-3">제9조 (책임 제한)</h2>
            <p className="text-slate-400">
              회사는 천재지변, 불가항력, 이용자의 귀책사유로 인한 손해에 대해서는 책임을 지지 않습니다. 회사는 서비스를 이용하여 기대하는 수익을 얻지 못하거나 서비스를 통한 투자로 인한 손실에 대해 책임을 지지 않습니다.
            </p>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-slate-100 mb-3">제10조 (준거법 및 관할)</h2>
            <p className="text-slate-400">
              이 약관은 대한민국 법률에 따라 해석되며, 서비스 이용으로 발생한 분쟁에 대해서는 민사소송법상의 관할법원을 제1심 법원으로 합니다.
            </p>
          </section>

        </div>

        <div className="mt-12 pt-8 border-t border-slate-800 flex gap-4 text-sm text-slate-400">
          <Link href="/legal/privacy" className="hover:text-slate-100 transition-colors">개인정보처리방침 →</Link>
          <Link href="/help" className="hover:text-slate-100 transition-colors">도움말</Link>
          <Link href="/" className="hover:text-slate-100 transition-colors">홈으로</Link>
        </div>
      </div>
    </div>
  );
}
