import json
import os
import socket
import subprocess
import sys
import unittest

from app import app


class AppTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_home_returns_application_details(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.is_json)
        self.assertEqual(
            response.get_json(),
            {
                "application": os.getenv("APP_NAME", "rke2-project"),
                "version": os.getenv("APP_VERSION", "1.0.0"),
                "hostname": socket.gethostname(),
            },
        )

    def test_health_returns_healthy(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.is_json)
        self.assertEqual(
            response.get_json(),
            {
                "status": "healthy",
                "version": os.getenv("APP_VERSION", "1.0.0"),
            },
        )

    def test_environment_configures_name_and_version(self):
        # A fresh process reads configuration as it would at container startup.
        script = (
            "import json; from app import app; "
            "client = app.test_client(); "
            "print(json.dumps([client.get('/').get_json(), "
            "client.get('/health').get_json()]))"
        )
        result = subprocess.run(
            [sys.executable, "-c", script],
            env={**os.environ, "APP_NAME": "ci-demo", "APP_VERSION": "2.3.4"},
            capture_output=True,
            text=True,
            check=True,
            timeout=10,
        )
        home, health = json.loads(result.stdout)
        self.assertEqual(home["application"], "ci-demo")
        self.assertEqual(home["version"], "2.3.4")
        self.assertEqual(health["version"], "2.3.4")

    def test_unknown_route_returns_not_found(self):
        self.assertEqual(self.client.get("/missing").status_code, 404)


if __name__ == "__main__":
    unittest.main()
