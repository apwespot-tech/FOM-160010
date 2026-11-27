from unittest import mock

from django.db.utils import OperationalError
from django.test import TestCase

HEALTH_URL = "/api/health"


class HealthEndpointTests(TestCase):
    def test_health_reports_online_database(self) -> None:
        response = self.client.get(HEALTH_URL)
        payload = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["database"]["status"], "ok")
        self.assertIsNotNone(payload["database"]["version"])

    def test_health_reports_unavailable_database(self) -> None:
        with mock.patch("finance_planner.api.connection") as connection_mock:
            connection_mock.cursor.side_effect = OperationalError("База данных недоступна")
            response = self.client.get(HEALTH_URL)

        payload = response.json()

        self.assertEqual(response.status_code, 503)
        self.assertEqual(payload["status"], "degraded")
        self.assertEqual(payload["database"]["status"], "unavailable")
        self.assertIsNone(payload["database"]["version"])
