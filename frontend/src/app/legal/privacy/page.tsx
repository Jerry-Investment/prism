import Link from "next/link";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "개인정보처리방침 — PRISM",
  description: "PRISM 개인정보처리방침. 수집 항목, 이용 목적, 보관 기간을 안내합니다.",
};

export default function PrivacyPage() {
  return (
    <div className="min-h-screen bg-slate-900 text-slate-100">
      <nav className="border-b border-slate-800 px-6 py-4 flex items-center justify-between">
        <Link href="/" className="text-xl font-bold text-green-400">PRISM</Link>
        <div className="flex items-center gap-4 text-sm text-slate-400">
          <Link href="/legal/terms" className="hover:text-slate-100 transition-colors">이용약관</Link>
          <Link href="/login" className="hover:text-slate-100 transition-colors">로그인</Link>
        </div>
      </nav>

      <div className="max-w-3xl mx-auto px-6 py-16">
        <h1 className="text-3xl font-bold mb-2">개인정보처리방침</h1>
        <p className="text-slate-500 text-sm mb-10">시행일: 2026년 1월 1일</p>

        <div className="space-y-8 text-slate-300 text-sm leading-relaxed">

          <section>
            <h2 className="text-lg font-semibold text-slate-100 mb-3">1. 개인정보의 수집 및 이용 목적</h2>
            <p className="text-slate-400">
              PRISM(이하 &quot;회사&quot;)은 다음의 목적을 위하여 개인정보를 처리합니다. 처리하는 개인정보는 다음 목적 이외의 용도로 사용되지 않으며, 이용 목적이 변경될 시에는 별도 동의를 받는 등 필요한 조치를 이행합니다.
            </p>
            <ul className="mt-3 space-y-2 list-disc list-inside text-slate-400">
              <li>회원가입 및 관리: 회원 식별, 서비스 이용 계약 체결</li>
              <li>서비스 제공: 백테스트 실행, 전략 저장, 모의 투자 기능 제공</li>
              <li>고객 지원: 문의 처리, 공지사항 전달</li>
              <li>서비스 개선: 이용 통계 분석, 신규 서비스 개발</li>
            </ul>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-slate-100 mb-3">2. 수집하는 개인정보 항목</h2>
            <div className="overflow-x-auto">
              <table className="w-full text-sm border-collapse">
                <thead>
                  <tr className="border-b border-slate-700">
                    <th className="text-left py-2 px-3 text-slate-300 font-semibold">구분</th>
                    <th className="text-left py-2 px-3 text-slate-300 font-semibold">수집 항목</th>
                    <th className="text-left py-2 px-3 text-slate-300 font-semibold">수집 방법</th>
                  </tr>
                </thead>
                <tbody className="text-slate-400">
                  <tr className="border-b border-slate-800">
                    <td className="py-2 px-3">필수</td>
                    <td className="py-2 px-3">이메일, 비밀번호(암호화 저장)</td>
                    <td className="py-2 px-3">회원가입 시</td>
                  </tr>
                  <tr className="border-b border-slate-800">
                    <td className="py-2 px-3">선택</td>
                    <td className="py-2 px-3">이름(닉네임)</td>
                    <td className="py-2 px-3">회원가입 시</td>
                  </tr>
                  <tr className="border-b border-slate-800">
                    <td className="py-2 px-3">자동 수집</td>
                    <td className="py-2 px-3">접속 IP, 접속 시간, 서비스 이용 기록</td>
                    <td className="py-2 px-3">서비스 이용 중</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-slate-100 mb-3">3. 개인정보 보유 및 이용 기간</h2>
            <ul className="space-y-2 list-disc list-inside text-slate-400">
              <li>회원 정보: 회원 탈퇴 시까지</li>
              <li>서비스 이용 기록: 3년 (통신비밀보호법 등 관계 법령에 따라)</li>
              <li>탈퇴 후 지체 없이 파기. 단, 법령상 보존 의무가 있는 정보는 해당 기간 동안 보관</li>
            </ul>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-slate-100 mb-3">4. 개인정보의 제3자 제공</h2>
            <p className="text-slate-400">
              회사는 원칙적으로 이용자의 개인정보를 제3자에게 제공하지 않습니다. 다만, 다음의 경우에는 예외로 합니다:
            </p>
            <ul className="mt-3 space-y-1 list-disc list-inside text-slate-400">
              <li>이용자가 사전에 동의한 경우</li>
              <li>법령의 규정에 의거하거나 수사 목적으로 법령에 정해진 절차와 방법에 따라 수사기관의 요구가 있는 경우</li>
            </ul>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-slate-100 mb-3">5. 개인정보 처리의 위탁</h2>
            <div className="overflow-x-auto">
              <table className="w-full text-sm border-collapse">
                <thead>
                  <tr className="border-b border-slate-700">
                    <th className="text-left py-2 px-3 text-slate-300 font-semibold">수탁 업체</th>
                    <th className="text-left py-2 px-3 text-slate-300 font-semibold">위탁 업무</th>
                  </tr>
                </thead>
                <tbody className="text-slate-400">
                  <tr className="border-b border-slate-800">
                    <td className="py-2 px-3">Amazon Web Services (AWS)</td>
                    <td className="py-2 px-3">서버 운영, 데이터 저장</td>
                  </tr>
                  <tr className="border-b border-slate-800">
                    <td className="py-2 px-3">Sentry</td>
                    <td className="py-2 px-3">오류 모니터링 (비식별 처리 후 전송)</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-slate-100 mb-3">6. 개인정보의 파기</h2>
            <p className="text-slate-400">
              회사는 개인정보 보유 기간의 경과, 처리 목적 달성 등 개인정보가 불필요하게 되었을 때에는 지체없이 해당 개인정보를 파기합니다. 전자적 파일 형태의 정보는 복구 및 재생할 수 없는 기술적 방법을 사용하여 완전하게 삭제합니다.
            </p>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-slate-100 mb-3">7. 이용자의 권리</h2>
            <p className="text-slate-400 mb-2">이용자는 다음의 권리를 행사할 수 있습니다:</p>
            <ul className="space-y-1 list-disc list-inside text-slate-400">
              <li>개인정보 열람 요청</li>
              <li>오류 등이 있을 경우 정정 요청</li>
              <li>삭제(회원 탈퇴 포함) 요청</li>
              <li>처리 정지 요청</li>
            </ul>
            <p className="text-slate-400 mt-3">
              권리 행사는 <a href="mailto:privacy@prism.kr" className="text-green-400 hover:text-green-300">privacy@prism.kr</a>로 이메일 요청 또는 계정 설정 페이지에서 직접 처리하실 수 있습니다.
            </p>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-slate-100 mb-3">8. 개인정보 보호 책임자</h2>
            <div className="bg-slate-800 border border-slate-700 rounded-xl p-4 text-slate-400">
              <div className="mb-1"><strong className="text-slate-300">개인정보 보호 책임자</strong></div>
              <div>이메일: <a href="mailto:privacy@prism.kr" className="text-green-400 hover:text-green-300">privacy@prism.kr</a></div>
            </div>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-slate-100 mb-3">9. 쿠키 사용</h2>
            <p className="text-slate-400">
              현재 서비스는 로그인 세션 유지를 위해 <code className="bg-slate-800 px-1 py-0.5 rounded text-green-400">localStorage</code>를 사용합니다. 별도의 추적 쿠키는 사용하지 않습니다.
            </p>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-slate-100 mb-3">10. 개인정보처리방침 변경</h2>
            <p className="text-slate-400">
              이 개인정보처리방침은 시행일로부터 적용됩니다. 내용의 추가·삭제 및 수정이 있을 시에는 시행일 7일 전부터 공지합니다.
            </p>
          </section>

        </div>

        <div className="mt-12 pt-8 border-t border-slate-800 flex gap-4 text-sm text-slate-400">
          <Link href="/legal/terms" className="hover:text-slate-100 transition-colors">이용약관 →</Link>
          <Link href="/help" className="hover:text-slate-100 transition-colors">도움말</Link>
          <Link href="/" className="hover:text-slate-100 transition-colors">홈으로</Link>
        </div>
      </div>
    </div>
  );
}
