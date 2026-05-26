"use client";

import Link from "next/link";
import { FaGithub, FaGlobeEurope } from "react-icons/fa";
import { IoLogoLinkedin } from "react-icons/io";

export default function Footer() {
  return (
    <footer className="border-t border-border mt-auto py-6 px-6">
      <div className="max-w-7xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4 text-xs text-muted-foreground">
        {/* Left */}
        <div className="flex items-center gap-4">
          <span className="font-semibold text-foreground">Hermes</span>
          <span>© 2026 Nathan Ivor Sequeira</span>
        </div>

        {/* Right */}
        <div className="flex items-center gap-4 flex-wrap">
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

          <Link href="/dlq" className="hover:text-foreground transition-colors">
            DLQ
          </Link>

          <div className="w-px h-3 bg-border mx-1" />

          {/* Social Icons */}
          <a
            href="https://github.com/Nathan-sudo-pycharm"
            target="_blank"
            rel="noopener noreferrer"
            className="hover:text-foreground transition-colors"
            aria-label="GitHub"
          >
            <FaGithub className="w-4 h-4" />
          </a>

          <a
            href="https://www.linkedin.com/in/nathan-sequeira214652/"
            target="_blank"
            rel="noopener noreferrer"
            className="hover:text-foreground transition-colors"
            aria-label="LinkedIn"
          >
            <IoLogoLinkedin className="w-4 h-4" />
          </a>

          <a
            href="https://nathansequeirafinal.vercel.app/"
            target="_blank"
            rel="noopener noreferrer"
            className="hover:text-foreground transition-colors"
            aria-label="Portfolio"
          >
            <FaGlobeEurope className="w-4 h-4" />
          </a>
        </div>
      </div>
    </footer>
  );
}
