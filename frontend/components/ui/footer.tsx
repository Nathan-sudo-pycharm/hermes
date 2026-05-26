export default function Footer() {
  return (
    <footer className="border-t border-border bg-card mt-auto">
      <div className="px-6 py-12 grid grid-cols-4 gap-8">
        {/* Branding */}
        <div className="space-y-3">
          <h3 className="font-semibold text-foreground">Hermes</h3>
          <p className="text-sm text-muted-foreground leading-relaxed">
            Distributed workflow orchestration platform for reliable, scalable
            task execution.
          </p>
        </div>

        {/* Platform */}
        <div className="space-y-3">
          <h4 className="font-semibold text-foreground">Platform</h4>
          <ul className="space-y-2 text-sm text-muted-foreground">
            <li>
              <a href="#" className="hover:text-foreground transition-colors">
                Dashboard
              </a>
            </li>
            <li>
              <a href="#" className="hover:text-foreground transition-colors">
                Executions
              </a>
            </li>
            <li>
              <a href="#" className="hover:text-foreground transition-colors">
                Workers
              </a>
            </li>
            <li>
              <a href="#" className="hover:text-foreground transition-colors">
                DLQ
              </a>
            </li>
          </ul>
        </div>

        {/* Stack */}
        <div className="space-y-3">
          <h4 className="font-semibold text-foreground">Stack</h4>
          <ul className="space-y-2 text-sm text-muted-foreground">
            <li>
              <a href="#" className="hover:text-foreground transition-colors">
                API Reference
              </a>
            </li>
            <li>
              <a href="#" className="hover:text-foreground transition-colors">
                Documentation
              </a>
            </li>
            <li>
              <a href="#" className="hover:text-foreground transition-colors">
                SDKs
              </a>
            </li>
            <li>
              <a href="#" className="hover:text-foreground transition-colors">
                Examples
              </a>
            </li>
          </ul>
        </div>

        {/* Observability */}
        <div className="space-y-3">
          <h4 className="font-semibold text-foreground">Observability</h4>
          <ul className="space-y-2 text-sm text-muted-foreground">
            <li>
              <a href="#" className="hover:text-foreground transition-colors">
                Logs
              </a>
            </li>
            <li>
              <a href="#" className="hover:text-foreground transition-colors">
                Metrics
              </a>
            </li>
            <li>
              <a href="#" className="hover:text-foreground transition-colors">
                Alerts
              </a>
            </li>
            <li>
              <a href="#" className="hover:text-foreground transition-colors">
                Status
              </a>
            </li>
          </ul>
        </div>
      </div>

      <div className="border-t border-border px-6 py-4 text-center text-xs text-muted-foreground">
        © 2026 Hermes. All rights reserved.
      </div>
    </footer>
  );
}
