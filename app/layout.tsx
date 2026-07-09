import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "有価証券報告書AI分析ツール",
  description: "EDINET APIとOpenAI APIで有価証券報告書を整理・分析します。",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="ja">
      <body>{children}</body>
    </html>
  );
}
