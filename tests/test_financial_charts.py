import unittest

class FinancialChartSpecTest(unittest.TestCase):
    def test_invalid_chart_params_return_error(self):
        from expense_agent.charting import build_financial_chart_spec

        result = build_financial_chart_spec(
            payments=[],
            chart_type="exploding_pyramid",
            visual_mode="2d",
            metric="amount",
            period="2026-05",
        )

        self.assertEqual(result["status"], "error")
        self.assertIn("chart_type", result["error_message"])

    def test_groups_payments_by_category_for_bar_chart(self):
        from expense_agent.charting import build_financial_chart_spec

        result = build_financial_chart_spec(
            payments=[
                {"amount": 100, "notes": "Edesur - luz", "period": "2026-05", "status": "paid", "currency": "ARS"},
                {"amount": 50, "notes": "Metrogas", "period": "2026-05", "status": "paid", "currency": "ARS"},
                {"amount": 25, "notes": "Edesur - luz", "period": "2026-05", "status": "pending", "currency": "ARS"},
            ],
            chart_type="bar",
            visual_mode="2d",
            metric="amount",
            period="2026-05",
            group_by="category",
        )

        self.assertEqual(result["status"], "success")
        spec = result["chart_spec"]
        self.assertEqual(spec["chartType"], "bar")
        self.assertEqual(spec["mode"], "2d")
        self.assertEqual(spec["option"]["xAxis"]["data"], ["luz", "gas"])
        self.assertEqual(spec["option"]["series"][0]["data"], [125.0, 50.0])

    def test_category_overrides_drive_grouping(self):
        from expense_agent.charting import build_financial_chart_spec

        result = build_financial_chart_spec(
            payments=[
                {"amount": 8000, "notes": "MacBook Pro", "period": "2026-05", "status": "paid", "currency": "USD"},
                {"amount": 198000, "notes": "Mercedes AMG", "period": "2026-05", "status": "paid", "currency": "USD"},
                {"amount": 41666.67, "notes": "Préstamo Galicia", "period": "2026-06", "status": "pending", "currency": "USD"},
                {"amount": 20, "notes": "Claude Pro", "period": "2026-05", "status": "paid", "currency": "USD"},
                {"amount": 20, "notes": "ChatGPT Plus", "period": "2026-05", "status": "paid", "currency": "USD"},
                {"amount": 10500, "notes": "Burger comida", "period": "2026-05", "status": "paid", "currency": "ARS"},
            ],
            chart_type="bar",
            visual_mode="2d",
            metric="amount",
            group_by="category",
            category_overrides={
                "MacBook Pro": "tecnología",
                "Mercedes AMG": "vehículo",
                "Préstamo Galicia": "financiación",
                "Claude Pro": "suscripciones",
                "ChatGPT Plus": "suscripciones",
                "Burger comida": "comida",
            },
        )

        self.assertEqual(result["status"], "success")
        labels = result["chart_spec"]["option"]["xAxis"]["data"]
        self.assertIn("vehículo", labels)
        self.assertIn("tecnología", labels)
        self.assertIn("financiación", labels)
        self.assertIn("suscripciones", labels)
        self.assertIn("comida", labels)
        self.assertNotIn("otros", labels)

    def test_category_overrides_drive_3d_category_axis(self):
        from expense_agent.charting import build_financial_chart_spec

        result = build_financial_chart_spec(
            payments=[
                {"amount": 8000, "notes": "MacBook Pro", "period": "2026-05", "status": "paid", "currency": "USD"},
                {"amount": 198000, "notes": "Mercedes AMG", "period": "2026-05", "status": "paid", "currency": "USD"},
            ],
            chart_type="category_month_bar3d",
            visual_mode="3d",
            metric="amount",
            group_by="category",
            secondary_group_by="period",
            category_overrides={
                "MacBook Pro": "tecnología",
                "Mercedes AMG": "vehículo",
            },
        )

        self.assertEqual(result["status"], "success")
        labels = result["chart_spec"]["option"]["xAxis3D"]["data"]
        self.assertEqual(labels, ["tecnología", "vehículo"])

    def test_visualization_agent_is_instructed_to_categorize_with_overrides(self):
        from pathlib import Path

        agent_source = Path("expense_agent/subagents/agente_visualizacion.py").read_text()

        self.assertIn("get_chart_source_data", agent_source)
        self.assertIn("category_overrides", agent_source)

    def test_custom_chart_spec_allows_agent_authored_echarts_options(self):
        from expense_agent.charting import build_custom_chart_spec

        option = {
            "tooltip": {"trigger": "axis"},
            "dataset": {"source": [["Categoría", "Mayo"], ["vehículo", 198000], ["tecnología", 8000]]},
            "xAxis": {"type": "category"},
            "yAxis": {"type": "value"},
            "series": [{"type": "bar", "encode": {"x": "Categoría", "y": "Mayo"}}],
        }

        result = build_custom_chart_spec(
            title="Gastos por categoría",
            mode="2d",
            chart_type="custom_bar",
            option=option,
            insights=["vehículo domina el gasto."],
            source={"records": 2},
        )

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["chart_spec"]["option"]["dataset"]["source"][1][0], "vehículo")
        self.assertEqual(result["chart_spec"]["chartType"], "custom_bar")

    def test_custom_chart_spec_rejects_executable_options(self):
        from expense_agent.charting import build_custom_chart_spec

        result = build_custom_chart_spec(
            title="Unsafe",
            mode="2d",
            chart_type="custom",
            option={"tooltip": {"formatter": "function(){ alert(1) }"}},
        )

        self.assertEqual(result["status"], "error")
        self.assertIn("no permitidos", result["error_message"])

    def test_custom_chart_spec_forces_dark_chart_theme_defaults(self):
        from expense_agent.charting import build_custom_chart_spec

        result = build_custom_chart_spec(
            title="Dark",
            mode="2d",
            chart_type="custom",
            option={
                "xAxis": {"type": "category", "data": ["a"]},
                "yAxis": {"type": "value"},
                "series": [{"type": "bar", "data": [1]}],
            },
        )

        self.assertEqual(result["status"], "success")
        option = result["chart_spec"]["option"]
        self.assertEqual(option["backgroundColor"], "transparent")
        self.assertEqual(option["textStyle"]["color"], "#d4d4d8")
        self.assertEqual(option["xAxis"]["axisLabel"]["color"], "#a1a1aa")
        self.assertEqual(option["yAxis"]["splitLine"]["lineStyle"]["color"], "rgba(255,255,255,0.14)")

    def test_visualization_agent_has_custom_chart_tool(self):
        from pathlib import Path

        agent_source = Path("expense_agent/subagents/agente_visualizacion.py").read_text()

        self.assertIn("generate_custom_chart", agent_source)
        self.assertIn("opciones completas de ECharts", agent_source)

    def test_visualization_agent_is_told_not_to_expose_internal_data_language(self):
        from pathlib import Path

        agent_source = Path("expense_agent/subagents/agente_visualizacion.py").read_text()

        self.assertIn("No hables de datos internos", agent_source)
        self.assertIn("service_id", agent_source)
        self.assertIn("category_overrides", agent_source)

    def test_auto_selects_line_for_monthly_evolution(self):
        from expense_agent.charting import build_financial_chart_spec

        result = build_financial_chart_spec(
            payments=[
                {"amount": 100, "notes": "Luz", "period": "2026-04", "status": "paid", "currency": "ARS"},
                {"amount": 200, "notes": "Gas", "period": "2026-05", "status": "paid", "currency": "ARS"},
            ],
            chart_type="auto",
            visual_mode="auto",
            metric="amount",
            period="2026-05",
            group_by="period",
        )

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["chart_spec"]["chartType"], "line")
        self.assertEqual(result["chart_spec"]["mode"], "2d")

    def test_auto_selects_3d_for_category_by_month(self):
        from expense_agent.charting import build_financial_chart_spec

        result = build_financial_chart_spec(
            payments=[
                {"amount": 100, "notes": "Luz", "period": "2026-04", "status": "paid", "currency": "ARS"},
                {"amount": 200, "notes": "Gas", "period": "2026-05", "status": "paid", "currency": "ARS"},
            ],
            chart_type="auto",
            visual_mode="auto",
            metric="amount",
            period="2026-05",
            group_by="category",
            secondary_group_by="period",
        )

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["chart_spec"]["chartType"], "category_month_bar3d")
        self.assertEqual(result["chart_spec"]["mode"], "3d")

    def test_chart_spec_contains_no_executable_strings(self):
        from expense_agent.charting import build_financial_chart_spec, contains_executable_string

        result = build_financial_chart_spec(
            payments=[
                {"amount": 100, "notes": "javascript:alert(1)", "period": "2026-05", "status": "paid", "currency": "ARS"},
            ],
            chart_type="pie",
            visual_mode="2d",
            metric="amount",
            period="2026-05",
            group_by="category",
        )

        self.assertEqual(result["status"], "success")
        self.assertFalse(contains_executable_string(result["chart_spec"]["option"]))

    def test_pending_chart_specs_can_be_drained_for_nested_agent_tools(self):
        from expense_agent.charting import pop_pending_chart_specs, queue_pending_chart_spec

        self.assertEqual(pop_pending_chart_specs(), [])
        queue_pending_chart_spec({"id": "chart_nested", "title": "Nested", "option": {}})

        self.assertEqual(pop_pending_chart_specs(), [{"id": "chart_nested", "title": "Nested", "option": {}}])
        self.assertEqual(pop_pending_chart_specs(), [])


if __name__ == "__main__":
    unittest.main()
