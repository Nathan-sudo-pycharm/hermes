export function getToken(): string {
  if (typeof window === "undefined") return "";
  return localStorage.getItem("hermes_token") || "";
}

export function setToken(token: string): void {
  localStorage.setItem("hermes_token", token);
}

export function clearToken(): void {
  localStorage.removeItem("hermes_token");
}
