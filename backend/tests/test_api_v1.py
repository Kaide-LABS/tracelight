class TestHealthEndpoint:
    def test_health_returns_ok(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] in ["ok", "degraded"]

class TestTemplates:
    def test_templates_returns_list(self, client):
        resp = client.get("/api/v1/templates")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 3  # PE LBO, VC Portfolio, Real Estate DCF

class TestGenerateEndpoint:
    def test_generate_with_profile_override(self, client):
        """Full generation with explicit profile (no LLM)."""
        payload = {
            "profile_override": {
                "asset_class": "test",
                "num_entities": 5,
                "time_horizon_years": 1,
                "frequency": "quarterly",
                "variables": {
                    "revenue": {"distribution": "normal", "mean": 100, "std": 10}
                },
                "correlations": [],
                "temporal": {"autocorrelation": 0.0}
            },
            "output_format": "csv",
            "seed": 42
        }
        resp = client.post("/api/v1/generate", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "completed"
        assert data["validation_report"]["row_count"] == 20  # 5 entities × 4 quarters

    def test_generate_missing_profile_returns_422(self, client):
        """No LLM profiler and no profile_override → 422."""
        resp = client.post("/api/v1/generate", json={})
        assert resp.status_code == 422
