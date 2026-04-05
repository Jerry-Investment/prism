import type { Metadata } from "next";
import "./globals.css";
import AuthProvider from "@/components/AuthProvider";

export const metadata: Metadata = {
  title: {
    default: "PRISM — 한국 시장 백테스트 플랫폼",
    template: "%s — PRISM",
  },
  description: "KOSPI, KOSDAQ, 업비트 암호화폐 시장을 위한 전문 백테스트 및 모의 투자 플랫폼.",
  keywords: ["백테스트", "퀀트", "주식", "암호화폐", "전략", "KOSPI", "KOSDAQ", "업비트", "모의투자"],
  authors: [{ name: "PRISM" }],
  robots: { index: true, follow: true },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ko">
      <body className="min-h-screen bg-slate-900 text-slate-100">
        <AuthProvider>{children}</AuthProvider>
      </body>
    </html>
  );
}
