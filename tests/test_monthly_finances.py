import unittest
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import patch

from expense_agent import tools


class FakeCursor:
    def __init__(self, docs):
        self.docs = docs

    def sort(self, *_args):
        return self

    async def to_list(self, length=None):
        return self.docs[:length] if length else self.docs


class FakeCollection:
    def __init__(self, docs=None):
        self.docs = docs or []

    async def update_one(self, query, update, upsert=False):
        for doc in self.docs:
            if all(doc.get(key) == value for key, value in query.items()):
                doc.update(update.get("$set", {}))
                return SimpleNamespace(upserted_id=None)

        if not upsert:
            return SimpleNamespace(upserted_id=None)

        new_doc = {"_id": "new-id", **query, **update.get("$setOnInsert", {}), **update.get("$set", {})}
        self.docs.append(new_doc)
        return SimpleNamespace(upserted_id="new-id")

    async def find_one(self, query):
        for doc in self.docs:
            if all(doc.get(key) == value for key, value in query.items()):
                return dict(doc)
        return None

    def find(self, query):
        def matches(doc):
            return all(doc.get(key) == value for key, value in query.items())

        return FakeCursor([dict(doc) for doc in self.docs if matches(doc)])


class MonthlyFinanceToolsTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.db = {
            "monthly_finances": FakeCollection(),
            "payments": FakeCollection(),
        }
        self.get_db_patch = patch.object(tools, "get_db", return_value=self.db)
        self.get_db_patch.start()
        self.addCleanup(self.get_db_patch.stop)

    async def test_save_monthly_finance_merges_budget_and_salary_for_demo_user(self):
        created = await tools.save_monthly_finance(period="2026-05", salary=2500000, currency="ARS")
        updated = await tools.save_monthly_finance(period="2026-05", budget=900000, notes="mes tranquilo")

        self.assertEqual(created["status"], "success")
        self.assertEqual(updated["status"], "success")

        saved = await tools.get_monthly_finance(period="2026-05")
        finance = saved["monthly_finance"]
        self.assertEqual(finance["user_id"], "demo_user")
        self.assertEqual(finance["period"], "2026-05")
        self.assertEqual(finance["salary"], 2500000)
        self.assertEqual(finance["budget"], 900000)
        self.assertEqual(finance["currency"], "ARS")
        self.assertEqual(finance["notes"], "mes tranquilo")
        self.assertRegex(finance["updated_at"], r"^20\d\d-")

    async def test_save_monthly_finance_rejects_invalid_period_and_empty_update(self):
        bad_period = await tools.save_monthly_finance(period="mayo", budget=1000)
        empty = await tools.save_monthly_finance(period="2026-05")

        self.assertEqual(bad_period["status"], "error")
        self.assertIn("YYYY-MM", bad_period["error_message"])
        self.assertEqual(empty["status"], "error")

    async def test_get_monthly_finance_summary_compares_spend_with_budget_and_salary(self):
        self.db["monthly_finances"].docs.append({
            "_id": "mf-1",
            "user_id": "demo_user",
            "period": "2026-05",
            "salary": 1000000,
            "budget": 400000,
            "currency": "ARS",
            "created_at": datetime(2026, 5, 1),
            "updated_at": datetime(2026, 5, 2),
        })
        self.db["payments"].docs.extend([
            {"user_id": "demo_user", "period": "2026-05", "amount": 100000, "status": "paid"},
            {"user_id": "demo_user", "period": "2026-05", "amount": 50000, "status": "pending"},
            {"user_id": "demo_user", "period": "2026-04", "amount": 999999, "status": "paid"},
        ])

        result = await tools.get_monthly_finance_summary(period="2026-05")

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["spent_total"], 150000)
        self.assertEqual(result["paid_total"], 100000)
        self.assertEqual(result["pending_total"], 50000)
        self.assertEqual(result["budget_remaining"], 250000)
        self.assertEqual(result["salary_remaining_after_spend"], 850000)
        self.assertEqual(result["budget_usage_pct"], 37.5)

    def test_agent_prompt_and_tools_expose_monthly_finance_capabilities(self):
        self.assertIn("save_monthly_finance", tools.__all__ if hasattr(tools, "__all__") else dir(tools))

        import expense_agent.agent as agent

        self.assertIn("monthly_finances", agent.INSTRUCTION)
        self.assertIn("save_monthly_finance", agent.INSTRUCTION)
        self.assertIn("get_monthly_finance_summary", agent.INSTRUCTION)
