"use client";

import { Zap } from "lucide-react";
import { Button } from "@/components/ui/button";

interface NavbarProps {
  currentPage: "dashboard" | "executions" | "workers" | "dlq";
  setCurrentPage: (
    page: "dashboard" | "executions" | "workers" | "dlq",
  ) => void;
}

export default function Navbar({ currentPage, setCurrentPage }: NavbarProps) {
  const navItems = [
    { id: "dashboard", label: "Dashboard" },
    { id: "executions", label: "Executions" },
    { id: "workers", label: "Workers" },
    { id: "dlq", label: "DLQ" },
  ] as const;

  return (
    <header className="border-b border-border bg-card sticky top-0 z-50">
      <div className="flex items-center justify-between px-6 py-4">
        {/* Logo */}
        <div className="flex items-center gap-2">
          <Zap className="w-6 h-6 text-info" />
          <span className="text-lg font-semibold text-foreground">Hermes</span>
        </div>

        {/* Nav Links */}
        <nav className="flex items-center gap-8">
          {navItems.map((item) => (
            <button
              key={item.id}
              onClick={() => setCurrentPage(item.id)}
              className={`text-sm font-medium transition-colors ${
                currentPage === item.id
                  ? "text-foreground border-b-2 border-info pb-1"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              {item.label}
            </button>
          ))}
        </nav>
      </div>
    </header>
  );
}
