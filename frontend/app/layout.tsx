import type { Metadata } from "next";
import { Geist } from "next/font/google";
import "./globals.css";
import Link from "next/link";

const geist = Geist({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Hermes",
  description: "Distributed Workflow Orchestration Platform",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body
        className={`${geist.className} bg-background text-foreground min-h-screen`}
      >
        <nav className="border-b border-border px-6 py-4 flex items-center gap-8">
          <span className="font-bold text-lg tracking-tight">⚡ Hermes</span>
          <div className="flex gap-6 text-xl text-muted-foreground">
            <Link href="/" className="hover:text-foreground transition-colors">
              Dashboard
            </Link>
            <Link
              href="/executions"
              className="hover:text-foreground transition-colors"
            >
              Executions
            </Link>
            <Link
              href="/workers"
              className="hover:text-foreground transition-colors"
            >
              Workers
            </Link>
            <Link
              href="/dlq"
              className="hover:text-foreground transition-colors"
            >
              DLQ
            </Link>
          </div>
        </nav>
        <main className="px-6 py-8 max-w-7xl mx-auto">{children}</main>
      </body>
    </html>
  );
}
