"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import {
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { getToken, setToken } from "@/lib/token";
import { getExecutions, login } from "@/lib/api";

interface Execution {
  id: string;
  state: string;
}

const COLORS = {
  Completed: "#10b981",
  Failed: "#ef4444",
  Running: "#f59e0b",
  Pending: "#64748b",
};

export default function Home() {
  const [token, setTokenState] = useState("");
  const [executions, setExecutions] = useState<Execution[]>([]);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    const t = getToken();
    if (t) {
      setTokenState(t);
      fetchData(t);
    }
  }, []);

  useEffect(() => {
    if (!token) return;
    const interval = setInterval(() => fetchData(token), 10000);
    return () => clearInterval(interval);
  }, [token]);

  async function fetchData(t: string) {
    const data = await getExecutions(t);
    setExecutions(data);
  }

  async function handleLogin() {
    try {
      const t = await login(email, password);
      setToken(t);
      setTokenState(t);
      fetchData(t);
    } catch {
      setError("Login failed. Check credentials.");
    }
  }

  const total = executions.length;
  const completed = executions.filter((e) => e.state === "COMPLETED").length;
  const failed = executions.filter((e) => e.state === "FAILED").length;
  const running = executions.filter((e) => e.state === "RUNNING").length;
  const pending = executions.filter((e) => e.state === "PENDING").length;

  const successPct = total > 0 ? Math.round((completed / total) * 100) : 0;
  const failedPct = total > 0 ? Math.round((failed / total) * 100) : 0;

  const barData = [
    { name: "Completed", value: completed },
    { name: "Failed", value: failed },
    { name: "Running", value: running },
    { name: "Pending", value: pending },
  ];

  const donutData = [
    { name: "Success", value: successPct },
    { name: "Failed", value: 100 - successPct },
  ];

  // ── Login ────────────────────────────────────────────────────
  if (!token) {
    return (
      <div className="max-w-sm mx-auto mt-20 space-y-4">
        <h1 className="text-2xl font-bold text-center">Hermes Login</h1>
        {error && <p className="text-red-500 text-sm text-center">{error}</p>}
        <input
          className="w-full px-3 py-2 rounded border border-border bg-background text-sm"
          placeholder="Email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
        />
        <input
          className="w-full px-3 py-2 rounded border border-border bg-background text-sm"
          placeholder="Password"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
        <Button className="w-full" onClick={handleLogin}>
          Sign In
        </Button>
      </div>
    );
  }

  // ── Dashboard ────────────────────────────────────────────────
  return (
    <div className="space-y-8">
      {/* Title */}
      <div>
        <h1 className="text-3xl font-bold text-foreground">Dashboard</h1>
        <p className="text-muted-foreground mt-1">
          Overview of your workflow executions
        </p>
      </div>

      {/* Stat Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-card border border-border rounded-lg p-6 backdrop-blur-sm">
          <div className="space-y-3">
            <p className="text-sm font-medium text-muted-foreground">
              Total Executions
            </p>
            <p className="text-4xl font-bold text-foreground">{total}</p>
            <p className="text-xs text-muted-foreground">All time</p>
          </div>
        </div>

        <div className="bg-card border border-border rounded-lg p-6 backdrop-blur-sm">
          <div className="space-y-3">
            <p className="text-sm font-medium text-muted-foreground">
              Completed
            </p>
            <p
              className="text-4xl font-bold"
              style={{ color: COLORS.Completed }}
            >
              {completed}
            </p>
            <p className="text-xs text-muted-foreground">
              {successPct}% success rate
            </p>
          </div>
        </div>

        <div className="bg-card border border-border rounded-lg p-6 backdrop-blur-sm">
          <div className="space-y-3">
            <p className="text-sm font-medium text-muted-foreground">Failed</p>
            <p className="text-4xl font-bold" style={{ color: COLORS.Failed }}>
              {failed}
            </p>
            <p className="text-xs text-muted-foreground">
              {failedPct}% failure rate
            </p>
          </div>
        </div>

        <div className="bg-card border border-border rounded-lg p-6 backdrop-blur-sm">
          <div className="space-y-3">
            <p className="text-sm font-medium text-muted-foreground">Running</p>
            <p className="text-4xl font-bold" style={{ color: COLORS.Running }}>
              {running}
            </p>
            <p className="text-xs text-muted-foreground">Currently active</p>
          </div>
        </div>
      </div>

      {/* Charts */}
      <div className="grid md:grid-cols-2 gap-6">
        {/* Bar Chart */}
        <div className="bg-card border border-border rounded-lg p-6 backdrop-blur-sm">
          <h2 className="text-lg font-semibold text-foreground mb-6">
            Executions by State
          </h2>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={barData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#27272a" />
              <XAxis dataKey="name" tick={{ fill: "#a1a1a6", fontSize: 12 }} />
              <YAxis tick={{ fill: "#a1a1a6", fontSize: 12 }} />
              <Tooltip
                contentStyle={{
                  backgroundColor: "#131317",
                  border: "1px solid #27272a",
                  borderRadius: "0.5rem",
                }}
                labelStyle={{ color: "#fafafa" }}
              />
              <Bar dataKey="value" radius={[8, 8, 0, 0]}>
                {barData.map((entry) => (
                  <Cell
                    key={entry.name}
                    fill={
                      COLORS[entry.name as keyof typeof COLORS] ?? "#6366f1"
                    }
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Donut Chart */}
        <div className="bg-card border border-border rounded-lg p-6 backdrop-blur-sm">
          <h2 className="text-lg font-semibold text-foreground mb-6">
            Success Rate
          </h2>
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie
                data={donutData}
                cx="50%"
                cy="50%"
                innerRadius={80}
                outerRadius={120}
                paddingAngle={2}
                dataKey="value"
              >
                <Cell fill={COLORS.Completed} />
                <Cell fill={COLORS.Failed} />
              </Pie>
              <Tooltip
                contentStyle={{
                  backgroundColor: "#131317",
                  border: "1px solid #27272a",
                  borderRadius: "0.5rem",
                }}
                labelStyle={{ color: "#fafafa" }}
              />
            </PieChart>
          </ResponsiveContainer>
          <div className="flex justify-center gap-6 mt-4 text-sm">
            <div className="flex items-center gap-2">
              <div
                className="w-3 h-3 rounded-full"
                style={{ backgroundColor: COLORS.Completed }}
              />
              <span className="text-muted-foreground">
                Success: {successPct}%
              </span>
            </div>
            <div className="flex items-center gap-2">
              <div
                className="w-3 h-3 rounded-full"
                style={{ backgroundColor: COLORS.Failed }}
              />
              <span className="text-muted-foreground">
                Failed: {failedPct}%
              </span>
            </div>
          </div>
        </div>
      </div>

      <p className="text-xs text-muted-foreground">
        Auto-refreshes every 10 seconds
      </p>
    </div>
  );
}
