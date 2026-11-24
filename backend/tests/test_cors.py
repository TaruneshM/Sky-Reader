import unittest
from starlette.testclient import TestClient

try:
    from backend.main import app
except ImportError:
    from main import app


class TestCORS(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_cors_allowed_origin_localhost_5174(self):
        response = self.client.get("/health", headers={"Origin": "http://localhost:5174"})
        # Fallback to any valid endpoint if /health returns 404
        if response.status_code == 404:
            response = self.client.get("/api/auth/me", headers={"Origin": "http://localhost:5174"})
        self.assertEqual(response.headers.get("access-control-allow-origin"), "http://localhost:5174")
        self.assertEqual(response.headers.get("access-control-allow-credentials"), "true")

    def test_cors_allowed_origin_127_0_0_1_5174(self):
        response = self.client.get("/api/auth/me", headers={"Origin": "http://127.0.0.1:5174"})
        self.assertEqual(response.headers.get("access-control-allow-origin"), "http://127.0.0.1:5174")
        self.assertEqual(response.headers.get("access-control-allow-credentials"), "true")

    def test_cors_allowed_origin_localhost_5173(self):
        response = self.client.get("/api/auth/me", headers={"Origin": "http://localhost:5173"})
        self.assertEqual(response.headers.get("access-control-allow-origin"), "http://localhost:5173")
        self.assertEqual(response.headers.get("access-control-allow-credentials"), "true")

    def test_cors_disallowed_origin_evil_example(self):
        response = self.client.get("/api/auth/me", headers={"Origin": "http://evil.example"})
        self.assertNotIn("access-control-allow-origin", response.headers)

    def test_cors_preflight_allowed_origin_localhost_5174(self):
        response = self.client.options(
            "/api/auth/login",
            headers={
                "Origin": "http://localhost:5174",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers.get("access-control-allow-origin"), "http://localhost:5174")
        self.assertEqual(response.headers.get("access-control-allow-credentials"), "true")

    def test_cors_preflight_disallowed_origin_evil_example(self):
        response = self.client.options(
            "/api/auth/login",
            headers={
                "Origin": "http://evil.example",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type",
            },
        )
        self.assertNotIn("access-control-allow-origin", response.headers)


if __name__ == "__main__":
    unittest.main()
