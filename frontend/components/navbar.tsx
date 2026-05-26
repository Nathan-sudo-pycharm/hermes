"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Zap } from "lucide-react";

const navItems = [
  { id: "dashboard", label: "Dashboard", href: "/" },
  { id: "executions", label: "Executions", href: "/executions" },
  { id: "workers", label: "Workers", href: "/workers" },
  { id: "dlq", label: "DLQ", href: "/dlq" },
];

export default function Navbar() {
  const pathname = usePathname();

  return (
    <header className="border-b border-border bg-card sticky top-0 z-50">
      <div className="flex items-center justify-between px-6 py-4">
        {/* Logo */}
        <div className="flex items-center gap-2">
          <Zap className="w-6 h-6 text-blue-500" />
          <span className="text-lg font-semibold text-foreground">Hermes</span>
        </div>

        {/* Nav Links */}
        <nav className="flex items-center gap-8">
          {navItems.map((item) => (
            <Link
              key={item.id}
              href={item.href}
              className={`text-sm font-medium transition-colors ${
                pathname === item.href
                  ? "text-foreground border-b-2 border-blue-500 pb-1"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              {item.label}
            </Link>
          ))}
        </nav>
      </div>
    </header>
  );
}
