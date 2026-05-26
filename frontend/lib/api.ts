const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8080";

// ── Auth ──────────────────────────────────────────────────────────────────────

export async function login(email: string, password: string): Promise<string> {
  const res = await fetch(`${BASE_URL}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) throw new Error("Login failed");
  const data = await res.json();
  return data.access_token;
}

// ── Workflows ─────────────────────────────────────────────────────────────────

export async function getExecutions(token: string) {
  const res = await fetch(`${BASE_URL}/workflows/executions`, {
    headers: { Authorization: `Bearer ${token}` },
    cache: "no-store",
  });
  if (!res.ok) return [];
  return res.json();
}

export async function getDefinitions(token: string) {
  const res = await fetch(`${BASE_URL}/workflows/definitions`, {
    headers: { Authorization: `Bearer ${token}` },
    cache: "no-store",
  });
  if (!res.ok) return [];
  return res.json();
}

export async function submitExecution(token: string, definitionId: string) {
  const res = await fetch(`${BASE_URL}/workflows/execute`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ definition_id: definitionId, input_payload: {} }),
  });
  if (!res.ok) throw new Error("Execution failed");
  return res.json();
}

// ── Workers ───────────────────────────────────────────────────────────────────

export async function getWorkers(token: string) {
  const res = await fetch(`${BASE_URL}/workers/`, {
    headers: { Authorization: `Bearer ${token}` },
    cache: "no-store",
  });
  if (!res.ok) return [];
  return res.json();
}

// ── DLQ ───────────────────────────────────────────────────────────────────────

export async function getDLQTasks(token: string) {
  const res = await fetch(`${BASE_URL}/dlq/tasks`, {
    headers: { Authorization: `Bearer ${token}` },
    cache: "no-store",
  });
  if (!res.ok) return [];
  return res.json();
}
