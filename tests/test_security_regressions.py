from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class SecurityRegressionTests(unittest.TestCase):
    def test_cloud_run_deployments_require_iam_authentication_by_default(self):
        for script in ("scripts/deploy_mcp.sh", "scripts/deploy_agent.sh"):
            source = (ROOT / script).read_text()

            self.assertIn("--no-allow-unauthenticated", source, script)
            self.assertNotIn("  --allow-unauthenticated", source, script)

    def test_cors_origins_are_not_wildcarded(self):
        source = (ROOT / "main.py").read_text()
        helper = (ROOT / "db/security.py").read_text()

        self.assertIn("cors_allowed_origins()", source)
        self.assertIn("CORS_ALLOW_ORIGINS", helper)
        self.assertNotIn('allow_origins=["*"]', source)

    def test_payments_api_does_not_trust_user_supplied_tenant_ids(self):
        source = (ROOT / "routes/payments.py").read_text()

        self.assertIn("current_user_id", source)
        self.assertIn('"user_id": current_user_id', source)
        self.assertNotIn("user_id: Optional[str] = Query(None)", source)

    def test_agent_runtime_user_and_session_are_not_hardcoded_demo_values(self):
        source = (ROOT / "routes/agent.py").read_text()

        self.assertIn("current_user_id", source)
        self.assertNotIn('USER_ID = "demo_user"', source)
        self.assertNotIn('SESSION_ID = "demo_session"', source)


if __name__ == "__main__":
    unittest.main()
