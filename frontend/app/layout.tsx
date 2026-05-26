import type { Metadata } from "next";
import { Geist } from "next/font/google";
import "./globals.css";
import Link from "next/link";
import Navbar from "@/components/navbar";
import Footer from "@/components/ui/footer";

const geist = Geist({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Hermes - Workflow Orchestration",
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
        suppressHydrationWarning
        className={`${geist.className} antialiased bg-background text-foreground min-h-screen`}
      >
        <Navbar />
        <main className="px-6 py-8 max-w-7xl mx-auto">{children}</main>
        <Footer />
      </body>
    </html>
  );
}
