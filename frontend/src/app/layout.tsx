import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Universal Intelligence Lab",
  description: "AI research operating system",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="bg-surface text-slate-100 antialiased">{children}</body>
    </html>
  );
}
