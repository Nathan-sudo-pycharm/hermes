"use client";

import { FaGithub, FaGlobeEurope } from "react-icons/fa";
import { IoLogoLinkedin } from "react-icons/io";

export default function Footer() {
  return (
    <footer className="border-t border-border mt-auto py-6 px-6">
      <div className="max-w-7xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4 text-xs text-muted-foreground">
        {/* Left */}
        <div className="flex items-center gap-4">
          <span className="font-semibold text-sm text-foreground">Hermes</span>
          <span className="text-sm">© 2026 Nathan Ivor Sequeira</span>
        </div>

        {/* Right — icons only */}
        <div className="flex items-center gap-4">
          <a
            href="https://github.com/Nathan-sudo-pycharm"
            target="_blank"
            rel="noopener noreferrer"
            className="hover:text-foreground transition-colors"
            aria-label="GitHub"
          >
            <FaGithub className="w-5 h-5" />
          </a>

          <a
            href="https://www.linkedin.com/in/nathan-sequeira214652/"
            target="_blank"
            rel="noopener noreferrer"
            className="hover:text-foreground transition-colors"
            aria-label="LinkedIn"
          >
            <IoLogoLinkedin className="w-5 h-5" />
          </a>

          <a
            href="https://nathansequeirafinal.vercel.app/"
            target="_blank"
            rel="noopener noreferrer"
            className="hover:text-foreground transition-colors"
            aria-label="Portfolio"
          >
            <FaGlobeEurope className="w-5 h-5" />
          </a>
        </div>
      </div>
    </footer>
  );
}
