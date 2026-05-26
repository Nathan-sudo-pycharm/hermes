from locust import HttpUser, task, between
import json

# Credentials — match what you registered
EMAIL    = "nathan@hermes.dev"
PASSWORD = "hermes123"

# The definition ID we've been using throughout the project
DEFINITION_ID = "f2524b1b-6bb2-41c9-ae88-f5d20ae1a3e6"


class HermesUser(HttpUser):
    """
    Simulates one user of the Hermes platform.
    Each virtual user:
      1. Logs in on startup to get a JWT token
      2. Repeatedly submits executions and reads the execution list
    wait_time: each user waits 1-3 seconds between tasks (realistic pacing)
    """
    wait_time = between(1, 3)
    token: str = ""

    def on_start(self):
        """
        Called once when a virtual user starts.
        Logs in and stores the JWT token for all subsequent requests.
        """
        response = self.client.post(
            "/auth/login",
            json={"email": EMAIL, "password": PASSWORD}
        )
        if response.status_code == 200:
            self.token = response.json()["access_token"]
        else:
            self.token = ""

    def auth_headers(self) -> dict:
        return {"Authorization": f"Bearer {self.token}"}

    @task(3)
    def submit_execution(self):
        """
        Most frequent task (weight 3).
        Submits a new workflow execution.
        This is the core write path — coordinator → Kafka → worker → gRPC → DB.
        """
        self.client.post(
            "/workflows/execute",
            json={
                "definition_id": DEFINITION_ID,
                "input_payload": {}
            },
            headers=self.auth_headers(),
            name="/workflows/execute"
        )

    @task(2)
    def list_executions(self):
        """
        Second most frequent (weight 2).
        Lists all workflow executions — tests DB read performance.
        """
        self.client.get(
            "/workflows/executions",
            headers=self.auth_headers(),
            name="/workflows/executions"
        )

    @task(1)
    def check_health(self):
        """
        Least frequent (weight 1).
        Hits the health endpoint — should always be fast.
        """
        self.client.get("/health", name="/health")

    @task(1)
    def list_workers(self):
        """
        Lists workers and circuit breaker states.
        Tests the workers endpoint under load.
        """
        self.client.get(
            "/workers/",
            headers=self.auth_headers(),
            name="/workers"
        )