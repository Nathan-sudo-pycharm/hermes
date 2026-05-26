"use client";

import { useEffect, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { getToken } from "@/lib/token";
import { getExecutions, getDefinitions, submitExecution } from "@/lib/api";

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

function StateBadge({ state }: { state: string }) {
  const variants: Record<string, string> = {
    COMPLETED: "bg-green-500/20 text-green-400 border-green-500/30",
    FAILED: "bg-red-500/20 text-red-400 border-red-500/30",
    RUNNING: "bg-yellow-500/20 text-yellow-400 border-yellow-500/30",
    PENDING: "bg-slate-500/20 text-slate-400 border-slate-500/30",
  };
  return (
    <span
      className={`text-xs px-2 py-0.5 rounded border font-medium ${variants[state] ?? variants.PENDING}`}
    >
      {state}
    </span>
  );
}

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
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Executions</h1>
        <Button onClick={handleSubmit} disabled={submitting}>
          {submitting ? "Submitting..." : "Submit Execution"}
        </Button>
      </div>

      {loading ? (
        <p className="text-muted-foreground text-sm">Loading...</p>
      ) : executions.length === 0 ? (
        <p className="text-muted-foreground text-sm">No executions yet.</p>
      ) : (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>ID</TableHead>
              <TableHead>State</TableHead>
              <TableHead>Started</TableHead>
              <TableHead>Completed</TableHead>
              <TableHead>Error</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {executions.map((e) => (
              <TableRow key={e.id}>
                <TableCell className="font-mono text-xs">
                  {e.id.slice(0, 8)}…
                </TableCell>
                <TableCell>
                  <StateBadge state={e.state} />
                </TableCell>
                <TableCell className="text-xs text-muted-foreground">
                  {new Date(e.started_at).toLocaleTimeString()}
                </TableCell>
                <TableCell className="text-xs text-muted-foreground">
                  {e.completed_at
                    ? new Date(e.completed_at).toLocaleTimeString()
                    : "—"}
                </TableCell>
                <TableCell className="text-xs text-red-400">
                  {e.error_msg ?? "—"}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}
    </div>
  );
}
