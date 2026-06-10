import unittest
from datetime import datetime

from routes.dashboard import _build_dashboard_payload, _payment_period_query


class DashboardPayloadTests(unittest.TestCase):
    def test_dashboard_summary_categories_budgets_and_movements(self):
        payments = [
            {
                "_id": "p1",
                "amount": 10000,
                "period": "2026-06",
                "payment_date": datetime(2026, 6, 3),
                "created_at": datetime(2026, 6, 3),
                "notes": "Supermercado",
                "status": "paid",
                "category": "Comida / Supermercado",
                "payment_method": "debito",
                "account": "Banco",
                "is_fixed": False,
            },
            {
                "_id": "p2",
                "amount": 25000,
                "period": "2026-06",
                "payment_date": datetime(2026, 6, 5),
                "created_at": datetime(2026, 6, 5),
                "notes": "Internet",
                "status": "pending",
                "service_id": "svc1",
            },
        ]
        previous = [{"amount": 20000}]
        services = [{"_id": "svc1", "name": "Fibra", "category": "utility"}]
        finance = {"salary": 100000, "budget": 50000, "created_at": datetime(2026, 6, 1)}
        budgets = [
            {"category": "Comida / Supermercado", "amount": 12000},
            {"category": "Servicios", "amount": 20000},
        ]

        result = _build_dashboard_payload(
            period="2026-06",
            payments=payments,
            previous_payments=previous,
            services=services,
            finance_doc=finance,
            category_budgets=budgets,
            movement_type="all",
        )

        self.assertEqual(result["summary"]["income"], 100000)
        self.assertEqual(result["summary"]["expenses"], 35000)
        self.assertEqual(result["summary"]["available_balance"], 65000)
        self.assertEqual(result["summary"]["budget_used_pct"], 70.0)
        self.assertEqual(result["summary"]["fixed_expenses"], 25000)
        self.assertEqual(result["summary"]["variable_expenses"], 10000)
        self.assertIn("Comida / Supermercado", [item["category"] for item in result["categories"]])
        self.assertIn("Servicios", [item["category"] for item in result["categories"]])
        budget_by_category = {item["category"]: item for item in result["budgets"]}
        self.assertEqual(budget_by_category["Comida / Supermercado"]["status"], "warning")
        self.assertEqual(budget_by_category["Servicios"]["status"], "exceeded")
        self.assertEqual(result["movements"][0]["tipo"], "gasto")
        self.assertEqual(len(result["topExpenses"]), 2)
        self.assertIn("debito", result["filters"]["paymentMethods"])

    def test_dashboard_can_filter_to_income_movements(self):
        result = _build_dashboard_payload(
            period="2026-06",
            payments=[{"_id": "p1", "amount": 1000, "payment_date": datetime(2026, 6, 2)}],
            previous_payments=[],
            services=[],
            finance_doc={"salary": 5000},
            category_budgets=[],
            movement_type="income",
        )

        self.assertEqual(len(result["movements"]), 1)
        self.assertEqual(result["movements"][0]["tipo"], "ingreso")

    def test_dashboard_classifies_rentas_as_housing(self):
        result = _build_dashboard_payload(
            period="2026-05",
            payments=[
                {
                    "_id": "p1",
                    "amount": 54000,
                    "payment_date": datetime(2026, 5, 30),
                    "notes": "Rentas del inmueble",
                }
            ],
            previous_payments=[],
            services=[],
            finance_doc=None,
            category_budgets=[],
            movement_type="all",
        )

        self.assertEqual(result["categories"][0]["category"], "Vivienda")
        self.assertEqual(result["movements"][0]["categoria"], "Vivienda")

    def test_period_query_includes_legacy_payments_without_period(self):
        query = _payment_period_query("user-1", "2026-05")

        self.assertEqual(query["user_id"], "user-1")
        self.assertIn({"period": "2026-05"}, query["$or"])
        self.assertEqual(query["$or"][1]["payment_date"]["$gte"], datetime(2026, 5, 1))
        self.assertEqual(query["$or"][1]["payment_date"]["$lt"], datetime(2026, 6, 1))


if __name__ == "__main__":
    unittest.main()
