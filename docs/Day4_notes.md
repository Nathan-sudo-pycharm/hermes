# Day 4 — Auth + Workflow Definition API

**Goal:** JWT register + login working, workflow definitions can be created and listed.

**Status: Complete**

---

## What Was Built

### Files Created

- `coordinator/app/auth.py` — bcrypt password hashing, JWT token creation and verification
- `coordinator/app/schemas.py` — Pydantic request/response models for all endpoints
- `coordinator/app/routers/auth.py` — POST /auth/register, POST /auth/login
- `coordinator/app/routers/workflows.py` — POST /workflows/definitions, GET /workflows/definitions, POST /workflows/execute, GET /workflows/executions, GET /workflows/executions/{id}
- `coordinator/app/routers/__init__.py` — empty file required for Python to treat folder as a package

### Files Modified

- `coordinator/app/main.py` — registered auth and workflows routers
- `coordinator/requirements.txt` — added `email-validator`, pinned `bcrypt==4.0.1`

---

## Endpoints Working

| Method | Path                       | Auth | What it does                                 |
| ------ | -------------------------- | ---- | -------------------------------------------- |
| POST   | /auth/register             | No   | Creates a new user, returns user info        |
| POST   | /auth/login                | No   | Validates credentials, returns JWT token     |
| POST   | /workflows/definitions     | JWT  | Creates a workflow definition with steps     |
| GET    | /workflows/definitions     | JWT  | Lists all workflow definitions               |
| POST   | /workflows/execute         | JWT  | Creates a workflow execution (PENDING state) |
| GET    | /workflows/executions      | JWT  | Lists all executions                         |
| GET    | /workflows/executions/{id} | JWT  | Gets one execution by ID                     |

---

## How JWT Auth Works

1. User registers via `POST /auth/register` — password is hashed with bcrypt and stored
2. User logs in via `POST /auth/login` — password is verified against hash, JWT token returned
3. Protected endpoints require `Authorization: Bearer <token>` header
4. `get_current_user` dependency decodes the token, extracts email, looks up user in DB
5. If token is missing, expired, or invalid — 401 is returned

---

## Test Results

**Register:**

```json
POST /auth/register
→ 201
{
  "id": "4bd06055-df15-4630-9379-ec5dcc239da8",
  "email": "test@hermes.dev",
  "created_at": "2026-05-19T05:45:32.624617Z"
}
```

**Login:**

```json
POST /auth/login
→ 200
{
  "access_token": "eyJhbGci...",
  "token_type": "bearer"
}
```

**Create Workflow Definition:**

```json
POST /workflows/definitions (with JWT)
→ 201
{
  "id": "c566eb0f-e19d-4cc0-9779-d202db7dd573",
  "name": "standard-pipeline",
  "steps": [{"name": "validate", "max_retries": 3, "timeout_seconds": 10}],
  "created_at": "2026-05-19T05:53:26.183927Z"
}
```

---

## Issues Encountered & Fixed

**`email-validator` not installed**
`EmailStr` in Pydantic requires `email-validator` as a separate package. Added to `requirements.txt`.

**bcrypt version incompatibility**
`passlib` 1.7.4 is not compatible with `bcrypt` 5.x — it tries to read `bcrypt.__about__.__version__` which no longer exists. Fixed by pinning `bcrypt==4.0.1` in `requirements.txt`.

**`__init__.py` missing in routers folder**
Python requires an `__init__.py` file in every folder that is treated as a package. Without it, `from app.routers import auth, workflows` fails with `ImportError`. Fixed by creating an empty `__init__.py` in `coordinator/app/routers/`.

**Swagger UI Authorize popup not showing Bearer field**
`OAuth2PasswordBearer` takes over the Authorize popup and expects form-encoded credentials, not JSON. Our login endpoint accepts JSON so the Swagger UI flow fails. This is a docs UI limitation — the actual auth system works correctly. Tested successfully via PowerShell `Invoke-WebRequest`.

---

## Key Concepts Learned

**bcrypt** — a password hashing algorithm designed to be slow on purpose. The slowness makes brute force attacks impractical. `passlib` wraps it with a clean API.

**JWT (JSON Web Token)** — a signed token containing a payload (email, expiry). Signed with a secret key so the server can verify it wasn't tampered with. No database lookup needed to validate the token — only to fetch the user after validation.

**Pydantic `EmailStr`** — validates that a string is a properly formatted email address. Requires the `email-validator` package.

**Python packages** — a folder must contain `__init__.py` to be importable as a package. This is a common mistake when creating new subfolders in a Python project.

---

_Day 4 complete — Hermes build, May 2026._
