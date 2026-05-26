"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { getToken, setToken } from "@/lib/token";
import { getExecutions, login } from "@/lib/api";

interface Execution {
  id: string;
  state: string;
}

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

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Dashboard</h1>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-muted-foreground">
              Total
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold">{total}</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-muted-foreground">
              Completed
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-green-500">{completed}</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-muted-foreground">
              Failed
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-red-500">{failed}</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-muted-foreground">
              Running
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-yellow-500">{running}</p>
          </CardContent>
        </Card>
      </div>
      <p className="text-xs text-muted-foreground">
        Auto-refreshes every 10 seconds
      </p>
    </div>
  );
}
