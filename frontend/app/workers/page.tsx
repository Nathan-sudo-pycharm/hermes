"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
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

function CBBadge({ state }: { state: string }) {
  const styles: Record<string, string> = {
    CLOSED: "bg-green-500/20 text-green-400 border-green-500/30",
    OPEN: "bg-red-500/20 text-red-400 border-red-500/30",
    HALF_OPEN: "bg-yellow-500/20 text-yellow-400 border-yellow-500/30",
  };
  return (
    <span
      className={`text-xs px-2 py-0.5 rounded border font-medium ${styles[state] ?? styles.CLOSED}`}
    >
      {state}
    </span>
  );
}

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
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Workers</h1>

      {loading ? (
        <p className="text-muted-foreground text-sm">Loading...</p>
      ) : workers.length === 0 ? (
        <p className="text-muted-foreground text-sm">No workers registered.</p>
      ) : (
        <div className="grid md:grid-cols-3 gap-4">
          {workers.map((w) => (
            <Card key={w.id}>
              <CardHeader className="pb-2">
                <CardTitle className="text-base flex items-center justify-between">
                  {w.id}
                  <CBBadge state={w.circuit_breaker.state} />
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-2 text-sm text-muted-foreground">
                <p>
                  Failures:{" "}
                  <span className="text-foreground font-medium">
                    {w.circuit_breaker.failure_count}
                  </span>
                </p>
                <p>
                  Last heartbeat:{" "}
                  <span className="text-foreground font-medium">
                    {w.last_heartbeat_at
                      ? new Date(w.last_heartbeat_at).toLocaleTimeString()
                      : "—"}
                  </span>
                </p>
                <p>
                  gRPC:{" "}
                  <span className="text-foreground font-mono text-xs">
                    {w.grpc_address}
                  </span>
                </p>
                {w.circuit_breaker.opened_at && (
                  <p>
                    Opened at:{" "}
                    <span className="text-red-400 text-xs">
                      {new Date(
                        w.circuit_breaker.opened_at,
                      ).toLocaleTimeString()}
                    </span>
                  </p>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
