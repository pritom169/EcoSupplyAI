"""Locust load test configuration for EcoSupplyAI.

Run with:
    locust -f tests/load/locustfile.py --host=http://localhost:8000

Or headless:
    locust -f tests/load/locustfile.py --host=http://localhost:8000 \
           --headless -u 50 -r 5 --run-time 2m
"""

from __future__ import annotations

from locust import HttpUser, between, task

from src.api_gateway.middleware.auth import create_access_token


class EcoSupplyUser(HttpUser):
    """Simulates a typical EcoSupplyAI user session."""

    wait_time = between(1, 5)

    def on_start(self) -> None:
        """Generate a JWT for authenticated requests."""
        self.token = create_access_token(
            {"sub": f"load-user-{self.environment.runner.user_count}", "roles": ["analyst"]}
        )
        self.headers = {"Authorization": f"Bearer {self.token}"}

    @task(5)
    def health_check(self) -> None:
        self.client.get("/health")

    @task(3)
    def ready_check(self) -> None:
        self.client.get("/ready")

    @task(2)
    def chat_message(self) -> None:
        self.client.post(
            "/api/v1/chat",
            json={
                "message": "What is the ESG score for GreenTex GmbH?",
                "stream": False,
            },
            headers=self.headers,
        )

    @task(1)
    def list_suppliers(self) -> None:
        self.client.get("/api/v1/suppliers/", headers=self.headers)
