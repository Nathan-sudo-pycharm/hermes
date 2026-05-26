"use client";

import { useEffect, useState } from "react";
import { getToken } from "@/lib/token";
import { getDLQTasks } from "@/lib/api";

interface DLQTask {
  id: string;
  execution_id: string;
  step_name: string;
  attempt_number: number;
  error_msg: string | null;
  completed_at: string | null;
}

export default function DLQPage() {
  const [tasks, setTasks] = useState<DLQTask[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = getToken();
    if (!token) return;
    getDLQTasks(token).then((data) => {
      setTasks(data);
      setLoading(false);
    });
  }, []);

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-foreground">
          Dead Letter Queue
        </h1>
        <p className="text-muted-foreground mt-1">
          Tasks that exhausted all retry attempts
        </p>
      </div>

      {/* Content */}
      {loading ? (
        <p className="text-muted-foreground text-sm">Loading...</p>
      ) : tasks.length === 0 ? (
        <div className="text-center py-12 text-muted-foreground">
          No dead-lettered tasks. Everything is running smoothly!
        </div>
      ) : (
        <div className="bg-card border border-border rounded-lg overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border bg-secondary/50">
                  <th className="px-6 py-4 text-left font-semibold text-foreground">
                    Task ID
                  </th>
                  <th className="px-6 py-4 text-left font-semibold text-foreground">
                    Step
                  </th>
                  <th className="px-6 py-4 text-left font-semibold text-foreground">
                    Attempts
                  </th>
                  <th className="px-6 py-4 text-left font-semibold text-foreground">
                    Error
                  </th>
                  <th className="px-6 py-4 text-left font-semibold text-foreground">
                    Time
                  </th>
                </tr>
              </thead>
              <tbody>
                {tasks.map((t) => (
                  <tr
                    key={t.id}
                    className="border-b border-border hover:bg-secondary/30 transition-colors"
                  >
                    <td className="px-6 py-4 font-mono text-xs text-muted-foreground">
                      {t.id.slice(0, 16)}…
                    </td>
                    <td className="px-6 py-4 text-foreground font-medium">
                      {t.step_name}
                    </td>
                    <td className="px-6 py-4">
                      <span className="inline-flex items-center justify-center w-8 h-8 rounded-full bg-secondary/50 text-foreground font-semibold text-sm">
                        {t.attempt_number}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      <span className="text-red-400 text-xs max-w-xs truncate inline-block">
                        {t.error_msg ?? "—"}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-xs text-muted-foreground whitespace-nowrap">
                      {t.completed_at
                        ? new Date(t.completed_at).toLocaleTimeString()
                        : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
