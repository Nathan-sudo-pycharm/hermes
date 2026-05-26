"use client";
import { useEffect, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { getToken } from "@/lib/token";
import { getExecutions, getDefinitions, submitExecution } from "@/lib/api";
import Footer from "@/components/ui/footer";

interface Execution {
  id: string;
  definition_id: string;
  state: string;
  started_at: string;
  completed_at: string | null;
  error_msg: string | null;
}

interface Definition {
  id: string;
  name: string;
}

const getStateStyle = (state: string) => {
  switch (state) {
    case "COMPLETED":
      return "bg-green-500/15 text-green-400 border-green-500/30";
    case "FAILED":
      return "bg-red-500/15 text-red-400 border-red-500/30";
    case "RUNNING":
      return "bg-yellow-500/15 text-yellow-400 border-yellow-500/30";
    case "PENDING":
      return "bg-slate-500/15 text-slate-400 border-slate-500/30";
    default:
      return "bg-slate-500/15 text-slate-400 border-slate-500/30";
  }
};

export default function ExecutionsPage() {
  const [executions, setExecutions] = useState<Execution[]>([]);
  const [definitions, setDefinitions] = useState<Definition[]>([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    const token = getToken();
    if (!token) return;

    Promise.all([getExecutions(token), getDefinitions(token)]).then(
      ([execs, defs]) => {
        setExecutions(execs);
        setDefinitions(defs);
        setLoading(false);
      },
    );

    const interval = setInterval(async () => {
      const data = await getExecutions(token);
      setExecutions(data);
    }, 10000);
    return () => clearInterval(interval);
  }, []);

  async function handleSubmit() {
    const token = getToken();
    if (!token || definitions.length === 0) return;
    setSubmitting(true);
    try {
      await submitExecution(token, definitions[0].id);
      const data = await getExecutions(token);
      setExecutions(data);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-foreground">Executions</h1>
          <p className="text-muted-foreground mt-1">
            All workflow executions and their status
          </p>
        </div>
        <Button
          onClick={handleSubmit}
          disabled={submitting || definitions.length === 0}
          variant="outline"
          className="border-blue-500 text-blue-400 hover:bg-blue-500/10"
        >
          {submitting ? "Submitting..." : "Submit Execution"}
        </Button>
      </div>

      {/* Table */}
      {loading ? (
        <p className="text-muted-foreground text-sm">Loading...</p>
      ) : executions.length === 0 ? (
        <p className="text-muted-foreground text-sm">No executions yet.</p>
      ) : (
        <div className="bg-card border border-border rounded-lg overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border bg-secondary/50">
                  <th className="px-6 py-4 text-left font-semibold text-foreground">
                    ID
                  </th>
                  <th className="px-6 py-4 text-left font-semibold text-foreground">
                    State
                  </th>
                  <th className="px-6 py-4 text-left font-semibold text-foreground">
                    Started
                  </th>
                  <th className="px-6 py-4 text-left font-semibold text-foreground">
                    Completed
                  </th>
                  <th className="px-6 py-4 text-left font-semibold text-foreground">
                    Error
                  </th>
                </tr>
              </thead>
              <tbody>
                {executions.map((e) => (
                  <tr
                    key={e.id}
                    className="border-b border-border hover:bg-secondary/30 transition-colors"
                  >
                    <td className="px-6 py-4 font-mono text-xs text-muted-foreground">
                      {e.id.slice(0, 16)}…
                    </td>
                    <td className="px-6 py-4">
                      <Badge
                        className={`${getStateStyle(e.state)} border capitalize`}
                      >
                        {e.state}
                      </Badge>
                    </td>
                    <td className="px-6 py-4 text-xs text-muted-foreground">
                      {new Date(e.started_at).toLocaleTimeString()}
                    </td>
                    <td className="px-6 py-4 text-xs text-muted-foreground">
                      {e.completed_at
                        ? new Date(e.completed_at).toLocaleTimeString()
                        : "—"}
                    </td>
                    <td className="px-6 py-4 text-xs text-red-400">
                      {e.error_msg ?? "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      <p className="text-xs text-muted-foreground">
        Auto-refreshes every 10 seconds
      </p>
    </div>
  );
}
