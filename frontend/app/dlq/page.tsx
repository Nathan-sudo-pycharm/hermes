"use client";

import { useEffect, useState } from "react";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
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
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Dead Letter Queue</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Tasks that exhausted all retry attempts.
        </p>
      </div>

      {loading ? (
        <p className="text-muted-foreground text-sm">Loading...</p>
      ) : tasks.length === 0 ? (
        <p className="text-muted-foreground text-sm">
          No dead-lettered tasks. System is healthy.
        </p>
      ) : (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Task ID</TableHead>
              <TableHead>Step</TableHead>
              <TableHead>Attempts</TableHead>
              <TableHead>Error</TableHead>
              <TableHead>Time</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {tasks.map((t) => (
              <TableRow key={t.id}>
                <TableCell className="font-mono text-xs">
                  {t.id.slice(0, 8)}…
                </TableCell>
                <TableCell className="text-sm">{t.step_name}</TableCell>
                <TableCell className="text-sm">{t.attempt_number}</TableCell>
                <TableCell className="text-xs text-red-400">
                  {t.error_msg ?? "—"}
                </TableCell>
                <TableCell className="text-xs text-muted-foreground">
                  {t.completed_at
                    ? new Date(t.completed_at).toLocaleTimeString()
                    : "—"}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}
    </div>
  );
}
