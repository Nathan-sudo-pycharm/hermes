# Hermes Engineering Notes — 2026-05-26

**Session:** Day 11 — Next.js Dashboard + shadcn/ui
**Engineer:** Nathan Ivor Sequeira

---

## 1. Goal of Today's Session

Build a frontend dashboard for Hermes that:

- Displays live workflow execution stats and state
- Shows worker health and circuit breaker status
- Lists dead-lettered tasks
- Allows submitting new executions from the UI
- Auto-refreshes every 10 seconds
- Looks production-credible using shadcn/ui components

---

## 2. What We Built

### Files Created

| File                               | Purpose                                              |
| ---------------------------------- | ---------------------------------------------------- |
| `frontend/`                        | Next.js 14 app scaffolded with TypeScript + Tailwind |
| `frontend/lib/api.ts`              | Centralised API calls to coordinator REST endpoints  |
| `frontend/lib/token.ts`            | JWT token management via localStorage                |
| `frontend/app/layout.tsx`          | Root layout — navbar + footer on every page          |
| `frontend/app/page.tsx`            | Dashboard — stat cards + bar chart + donut chart     |
| `frontend/app/executions/page.tsx` | Executions table with state badges + submit button   |
| `frontend/app/workers/page.tsx`    | Worker cards with circuit breaker state              |
| `frontend/app/dlq/page.tsx`        | Dead Letter Queue task table                         |
| `frontend/components/footer.tsx`   | Footer with 4 columns and GitHub link                |

### Dependencies Installed

| Package        | Purpose                                                     |
| -------------- | ----------------------------------------------------------- |
| `shadcn/ui`    | Component library — card, badge, table, tabs, button, chart |
| `lucide-react` | Icons (bundled with shadcn)                                 |
| `recharts`     | Chart library (bundled with shadcn chart component)         |
| `react-icons`  | Social icons for footer                                     |

### Files Modified

| File                      | Change                                            |
| ------------------------- | ------------------------------------------------- |
| `coordinator/app/main.py` | Added CORS middleware for `http://localhost:3000` |

---

## 3. Engineering Reasoning

### What each file does

**`lib/api.ts` — API layer**

Central file for all `fetch()` calls to the coordinator. Every page imports named functions like `getExecutions()`, `getWorkers()`, `getDLQTasks()` instead of writing raw fetch calls inline. If the coordinator URL changes, it changes in one place. All calls use `cache: "no-store"` to ensure fresh data on every request.

---

**`lib/token.ts` — Token management**

The coordinator requires a JWT Bearer token on every API call. This file wraps `localStorage` with three functions: `getToken()`, `setToken()`, `clearToken()`. All pages call `getToken()` on mount to retrieve the stored token. If no token exists, the dashboard shows a login form.

Uses a `typeof window === "undefined"` guard to prevent server-side rendering errors — `localStorage` only exists in the browser.

---

**`app/layout.tsx` — Root layout**

In Next.js App Router, `layout.tsx` wraps every page automatically. The navbar and footer are defined here once — no repetition across pages. The body uses `flex flex-col min-h-screen` with `flex-1` on `<main>` to push the footer to the bottom of every page regardless of content height.

---

**`app/page.tsx` — Dashboard**

Client component (`"use client"`) because it needs `localStorage` for the token and `setInterval` for auto-refresh. Shows a login form if no token is stored. After login, fetches executions and derives stats (total, completed, failed, running) from the array.

Two charts added using shadcn's chart component (built on Recharts):

- **Bar chart** — executions grouped by state, each bar colour-coded
- **Donut chart** — proportional breakdown of states with legend

Both charts use the same colour scheme as the stat cards and badges: green=completed, red=failed, yellow=running.

---

**`app/executions/page.tsx` — Executions table**

Fetches both executions and definitions on mount. The Submit Execution button calls `submitExecution()` using `definitions[0].id` — the first available definition. After submission, re-fetches the executions list so the new row appears immediately. State badges use inline className maps to apply colour-coded styles per state.

---

**`app/workers/page.tsx` — Workers grid**

Three cards in a responsive grid. Each card shows the worker ID, circuit breaker state badge, failure count, last heartbeat time, and gRPC address. If `opened_at` is set (circuit is OPEN or was recently OPEN), it shows in red. Auto-refreshes every 10 seconds.

---

**`app/dlq/page.tsx` — Dead Letter Queue**

Simple table showing all tasks where `state = DEAD_LETTERED`. Error messages rendered in red. If the DLQ is empty, shows a "System is healthy" message instead of an empty table.

---

**CORS middleware on coordinator**

Browsers enforce the Same-Origin Policy — a page at `localhost:3000` cannot call an API at `localhost:8080` unless the server explicitly allows it. Added `CORSMiddleware` to the coordinator's FastAPI app with `allow_origins=["http://localhost:3000"]`. Without this, every API call from the dashboard would be silently blocked by the browser.

---

### Why Next.js App Router over Pages Router

App Router is the current standard in Next.js 14+. It supports layouts natively (no need for `_app.tsx` wrapping), has better support for React Server Components, and is what all new Next.js projects should use. The entire dashboard is client-side (`"use client"`) since it needs browser APIs (localStorage, setInterval) — but the App Router structure is still correct.

### Why shadcn/ui over a full component library

shadcn/ui components are copied into your project — not installed as a black-box dependency. You own the code. This means full control over styling, no version lock-in, and components that integrate perfectly with Tailwind. For a portfolio project this is the right choice: it shows you understand the components, not just imported them.

---

## 4. Problems and Errors Encountered

### Problem 1 — Login failed: CORS blocked

After building the dashboard and attempting login, the browser returned "Login failed. Check credentials." even with correct credentials.

### Problem 2 — `npm run dev` run from wrong directory

Running `npm run dev` from `hermes/` root instead of `hermes/frontend/` caused:

```
npm error Missing script: "dev"
```

### Problem 3 — `lib/` folder created inside `app/` instead of `frontend/`

The `lib/` folder was created at `frontend/app/lib/` instead of `frontend/lib/`.

### Problem 4 — Submit Execution button appeared unresponsive

Clicking Submit Execution produced no visible feedback. The button was actually working (201 responses visible in Network tab) but the UI showed no confirmation.

---

## 5. Debugging Process

### Fix 1 — CORS blocked

**Root cause:** Browser enforces Same-Origin Policy. `localhost:3000` (Next.js) calling `localhost:8080` (coordinator) is a cross-origin request — blocked by default.

**Fix:** Added `CORSMiddleware` to `coordinator/app/main.py`:

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080"],
    allow_methods=["*"],
    allow_headers=["*"],
)
```

Rebuilt and restarted coordinator. Login worked immediately.

**Lesson:** Any time a browser app calls a different port or domain, CORS must be explicitly enabled on the server. This is a browser security feature, not a bug.

---

### Fix 2 — Wrong terminal directory

**Root cause:** `npm run dev` must be run from the directory containing `package.json`.

**Fix:** `cd frontend` then `npm run dev`.

---

### Fix 3 — `lib/` in wrong location

**Root cause:** Created inside `app/` by mistake.

**Fix:**

```powershell
Move-Item app\lib lib
```

---

### Fix 4 — Submit button appeared unresponsive

**Root cause:** The button worked correctly — 201 responses confirmed in browser Network tab. The new execution appeared in the table as RUNNING but blended with existing RUNNING rows. No visual toast/confirmation was implemented.

**Lesson:** Silent success is a UX problem. A future improvement would add a toast notification on successful submission.

---

## 6. Current Project Status

### Working

- Next.js dashboard running on `http://localhost:3000` ✅
- Login with JWT stored in localStorage ✅
- Dashboard: 4 stat cards + bar chart + donut chart, 10s auto-refresh ✅
- Executions page: full table with colour-coded badges, Submit button ✅
- Workers page: 3 cards with live circuit breaker state ✅
- DLQ page: dead-lettered tasks table ✅
- Footer: 4 columns with GitHub link, Stack, Observability links ✅
- CORS enabled on coordinator for localhost:3000 ✅

### Technical Debt / TODOs

| Item                              | Notes                                                                            |
| --------------------------------- | -------------------------------------------------------------------------------- |
| No toast on execution submit      | Silent success — user has no confirmation beyond table update                    |
| Token never expires in UI         | JWT expires server-side but UI doesn't detect this gracefully — shows blank data |
| No pagination on executions table | All executions loaded at once — will slow down with large datasets               |
| UI not mobile-optimised           | Works on desktop, responsive grid but not fully tested on mobile                 |
| v0.dev UI redesign pending        | Cleaner visual design generated via v0.dev — integration in separate session     |
| No loading skeletons              | Pages show "Loading..." text — shadcn skeleton components would look better      |
