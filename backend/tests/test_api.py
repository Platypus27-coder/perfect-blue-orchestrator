import os
import unittest
from pathlib import Path

os.environ["PERFECTBLUE_STATE_DIR"] = str(
    Path("backend/tests/.api-state").resolve()
)
os.environ["PERFECTBLUE_RUNTIME_TOKEN"] = "test-runtime-token"

try:
    from fastapi.testclient import TestClient

    from backend.main import app

    CLIENT = TestClient(app)
    API_AVAILABLE = True
except (ImportError, ModuleNotFoundError):
    CLIENT = None
    API_AVAILABLE = False


@unittest.skipUnless(API_AVAILABLE, "FastAPI integration dependencies are not installed")
class RuntimeApiTests(unittest.TestCase):
    @property
    def authenticated_headers(self):
        return {"Authorization": "Bearer test-runtime-token"}

    def test_health_is_public(self):
        response = CLIENT.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["ok"])

    def test_runtime_routes_require_the_configured_token(self):
        response = CLIENT.get("/state")
        self.assertEqual(response.status_code, 401)

        authenticated = CLIENT.get("/state", headers=self.authenticated_headers)
        self.assertEqual(authenticated.status_code, 200)
        self.assertGreaterEqual(len(authenticated.json()["agents"]), 9)

    def test_task_api_round_trip(self):
        created = CLIENT.post(
            "/api/v1/tasks",
            headers=self.authenticated_headers,
            json={"title": "API integration task", "status": "todo"},
        )
        self.assertEqual(created.status_code, 200)
        task_id = created.json()["task"]["id"]

        updated = CLIENT.post(
            f"/api/v1/tasks/{task_id}",
            headers=self.authenticated_headers,
            json={"status": "done"},
        )
        self.assertEqual(updated.status_code, 200)

        deleted = CLIENT.delete(
            f"/api/v1/tasks/{task_id}",
            headers=self.authenticated_headers,
        )
        self.assertEqual(deleted.status_code, 200)


if __name__ == "__main__":
    unittest.main()
