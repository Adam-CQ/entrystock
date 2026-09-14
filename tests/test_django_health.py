from django.test import SimpleTestCase


class HealthPageTests(SimpleTestCase):
    def test_health_page_returns_stable_success_payload(self) -> None:
        response = self.client.get("/health")

        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
