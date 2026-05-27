# Hermes Engineering Notes — 2026-05-27

**Session:** Day 13 — CI/CD with GitHub Actions
**Project:** Hermes — Distributed Workflow Orchestration Platform
**Engineer:** Nathan Ivor Sequeira

---

## 1. Goal of Today's Session

Set up a Continuous Integration pipeline using GitHub Actions that:

- Runs automatically on every push and pull request to `main`
- Validates coordinator and worker imports
- Verifies proto files and generated gRPC stubs are present
- Builds coordinator and worker Docker images
- Shows a live passing/failing badge on the GitHub repository

---

## 2. What We Built

### Files Created

| File                       | Purpose                               |
| -------------------------- | ------------------------------------- |
| `.github/workflows/ci.yml` | GitHub Actions CI pipeline definition |

### Files Modified

| File        | Change                           |
| ----------- | -------------------------------- |
| `README.md` | Added CI status badge at the top |

---

## 3. Engineering Reasoning

### What the pipeline does — step by step

The pipeline has two parallel jobs:

**Job 1: Import & Structure Check**

Runs on `ubuntu-latest` — matches the Linux environment our Docker containers use.

Steps in order:

1. **Checkout code** — clones the repo into the runner
2. **Set up Python 3.11** — matches the `python:3.11-slim` base image in our Dockerfiles
3. **Install coordinator dependencies** — `pip install -r requirements.txt` from `coordinator/`
4. **Install worker dependencies** — same for `worker/`
5. **Check coordinator imports** — runs 4 Python one-liners that import key modules. If any import fails (missing package, syntax error, broken dependency), the step fails and the pipeline stops
6. **Check worker imports** — same for worker modules
7. **Verify proto files** — uses `test -f` to confirm the `.proto` source files exist in all three locations
8. **Verify generated stubs** — confirms the four generated gRPC Python files exist

**Job 2: Docker Build Check**

Builds the coordinator and worker Docker images from scratch on the CI runner. If either Dockerfile has an error or a `pip install` step fails, this job fails. This catches broken dependencies before they reach production.

---

### Why GitHub Actions over other CI tools

- **Free for public repos** — no cost for this project
- **Native GitHub integration** — no external service to configure; pipelines live in the repo
- **YAML-based** — readable, version-controlled alongside the code
- **Large action marketplace** — `actions/checkout`, `actions/setup-python` are maintained by GitHub itself

### Why two separate jobs

Separating import checks from Docker build checks means:

- If imports fail, you know immediately without waiting for a full Docker build
- Both jobs run in parallel — faster feedback
- Failure is specific: "imports broke" vs "Dockerfile broke" are different problems

### Why environment variables in the CI config

The coordinator's `Settings` class (Pydantic) validates all required config fields at import time. If `JWT_SECRET_KEY` or `INTERNAL_GRPC_SECRET` are missing, the import fails immediately. CI provides fake values just enough to satisfy validation — the coordinator never actually connects to a database or Kafka in this job.

This is the correct pattern: import checks test code structure, not runtime behaviour.

---

## 4. Problems and Errors Encountered

### Problem 1 — CI pipeline not appearing on GitHub Actions tab

After first push, the Actions tab showed no workflows.

### Problem 2 — Import check failing: missing `JWT_SECRET_KEY` and `INTERNAL_GRPC_SECRET`

```
pydantic_core._pydantic_core.ValidationError: 2 validation errors for Settings
JWT_SECRET_KEY
  Field required
INTERNAL_GRPC_SECRET
  Field required
```

---

## 5. Debugging Process

### Fix 1 — Pipeline not appearing

**Root cause:** The `.github/workflows/ci.yml` file was not committed or the directory structure was incorrect on first attempt.

**Fix:** Re-created the file and pushed again. GitHub Actions picks up workflow files automatically on push — no manual registration needed.

---

### Fix 2 — Missing environment variables

**Root cause:** The CI YAML used `SECRET_KEY` as the environment variable name, but the coordinator's `config.py` (Pydantic Settings) expects `JWT_SECRET_KEY` and `INTERNAL_GRPC_SECRET`. Pydantic validates all required fields at instantiation — which happens at module import time — so the import check failed immediately.

**Investigation:** Error traceback in the GitHub Actions log clearly showed:

```
ValidationError: 2 validation errors for Settings
JWT_SECRET_KEY — Field required
INTERNAL_GRPC_SECRET — Field required
```

**Fix:** Updated the env section in the import check step:

```yaml
env:
  DATABASE_URL: postgresql://hermes:hermespass@localhost:5432/hermes
  JWT_SECRET_KEY: ci-test-secret-key-not-real
  INTERNAL_GRPC_SECRET: ci-test-grpc-secret-not-real
  KAFKA_BOOTSTRAP_SERVERS: localhost:9092
  KAFKA_TASKS_TOPIC: hermes.tasks
```

**Lesson:** When writing CI import checks for apps that use Pydantic Settings, always check what fields are marked as required in the Settings class and provide dummy values for all of them in the CI environment.

---

## 6. Current Project Status

### Working

- CI pipeline runs on every push to main ✅
- Import checks pass for both coordinator and worker ✅
- Proto file verification passes ✅
- Generated stub verification passes ✅
- Docker build check passes for both images ✅
- CI badge showing **passing** on GitHub repository README ✅

---

_End of Day 13 Engineering Notes_
