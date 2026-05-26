"use client";

import { useEffect, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Activity } from "lucide-react";
import { getToken } from "@/lib/token";
import { getWorkers } from "@/lib/api";

interface CircuitBreaker {
  state: string;
  failure_count: number;
  opened_at: string | null;
  next_retry_at: string | null;
}

interface Worker {
  id: string;
  grpc_address: string;
  last_heartbeat_at: string | null;
  circuit_breaker: CircuitBreaker;
}

const getCircuitBreakerBadgeStyle = (state: string) => {
  switch (state) {
    case "CLOSED":
      return "bg-green-500/15 text-green-400 border-green-500/30";
    case "OPEN":
      return "bg-red-500/15 text-red-400 border-red-500/30";
    case "HALF_OPEN":
      return "bg-yellow-500/15 text-yellow-400 border-yellow-500/30";
    default:
      return "bg-slate-500/15 text-slate-400 border-slate-500/30";
  }
};

const getCardBgStyle = (state: string) => {
  switch (state) {
    case "CLOSED":
      return "bg-green-500/10";
    case "OPEN":
      return "bg-red-500/10";
    case "HALF_OPEN":
      return "bg-yellow-500/10";
    default:
      return "bg-secondary/20";
  }
};

const getDotStyle = (state: string) => {
  switch (state) {
    case "CLOSED":
      return "bg-green-500";
    case "OPEN":
      return "bg-red-500";
    case "HALF_OPEN":
      return "bg-yellow-500";
    default:
      return "bg-slate-500";
  }
};

export default function WorkersPage() {
  const [workers, setWorkers] = useState<Worker[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = getToken();
    if (!token) return;

    getWorkers(token).then((data) => {
      setWorkers(data);
      setLoading(false);
    });

    const interval = setInterval(async () => {
      const data = await getWorkers(token);
      setWorkers(data);
    }, 10000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-foreground">Workers</h1>
        <p className="text-muted-foreground mt-1">
          Connected worker instances and their status
        </p>
      </div>

      {/* Content */}
      {loading ? (
        <p className="text-muted-foreground text-sm">Loading...</p>
      ) : workers.length === 0 ? (
        <p className="text-muted-foreground text-sm">No workers registered.</p>
      ) : (
        <div className="grid md:grid-cols-3 gap-6">
          {workers.map((w) => (
            <div
              key={w.id}
              className={`${getCardBgStyle(w.circuit_breaker.state)} border border-border rounded-lg p-6`}
            >
              <div className="space-y-4">
                {/* Worker ID + status dot */}
                <div className="flex items-center gap-3">
                  <div
                    className={`w-3 h-3 rounded-full shrink-0 ${getDotStyle(w.circuit_breaker.state)}`}
                  />
                  <h3 className="font-semibold text-foreground text-sm font-mono truncate">
                    {w.id}
                  </h3>
                </div>

                {/* Circuit Breaker State */}
                <div>
                  <p className="text-xs text-muted-foreground mb-2">
                    Circuit Breaker State
                  </p>
                  <Badge
                    className={`${getCircuitBreakerBadgeStyle(w.circuit_breaker.state)} border`}
                  >
                    {w.circuit_breaker.state}
                  </Badge>
                </div>

                {/* Failure Count */}
                <div className="pt-2 border-t border-border">
                  <p className="text-xs text-muted-foreground mb-1">
                    Failure Count
                  </p>
                  <p className="text-2xl font-bold text-foreground">
                    {w.circuit_breaker.failure_count}
                  </p>
                </div>

                {/* Last Heartbeat */}
                <div className="pt-2 border-t border-border">
                  <div className="flex items-center gap-2 mb-1">
                    <Activity className="w-4 h-4 text-blue-400" />
                    <p className="text-xs text-muted-foreground">
                      Last Heartbeat
                    </p>
                  </div>
                  <p className="text-xs text-muted-foreground">
                    {w.last_heartbeat_at
                      ? new Date(w.last_heartbeat_at).toLocaleTimeString()
                      : "—"}
                  </p>
                </div>

                {/* gRPC Address */}
                <div className="pt-2 border-t border-border">
                  <p className="text-xs text-muted-foreground mb-1">
                    gRPC Address
                  </p>
                  <p className="text-xs font-mono text-foreground">
                    {w.grpc_address}
                  </p>
                </div>

                {/* Opened At — only shown when circuit is OPEN */}
                {w.circuit_breaker.opened_at && (
                  <div className="pt-2 border-t border-border">
                    <p className="text-xs text-muted-foreground mb-1">
                      Opened At
                    </p>
                    <p className="text-xs text-red-400">
                      {new Date(
                        w.circuit_breaker.opened_at,
                      ).toLocaleTimeString()}
                    </p>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      <p className="text-xs text-muted-foreground">
        Auto-refreshes every 10 seconds
      </p>
    </div>
  );
}
