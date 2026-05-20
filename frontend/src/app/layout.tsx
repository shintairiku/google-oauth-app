import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "web-app-standard",
  description: "FastAPI + Next.js starter template",
};

type RootLayoutProps = Readonly<{
  children: React.ReactNode;
}>;

export default function RootLayout({ children }: RootLayoutProps) {
  return (
    <html lang="ja">
      <body>{children}</body>
    </html>
  );
}
