import unittest


class AgentChartSseTest(unittest.TestCase):
    def test_chart_payload_extracted_from_successful_tool_response(self):
        from routes.agent import _chart_payload_from_function_response

        function_response = type(
            "FunctionResponse",
            (),
            {
                "name": "generate_financial_chart",
                "response": {
                    "status": "success",
                    "chart_spec": {"id": "chart_1", "title": "Gastos", "option": {}},
                },
            },
        )()

        self.assertEqual(
            _chart_payload_from_function_response(function_response),
            {"id": "chart_1", "title": "Gastos", "option": {}},
        )

    def test_chart_payload_ignores_non_chart_tool_response(self):
        from routes.agent import _chart_payload_from_function_response

        function_response = type(
            "FunctionResponse",
            (),
            {"name": "save_expense", "response": {"status": "success"}},
        )()

        self.assertIsNone(_chart_payload_from_function_response(function_response))

    def test_pending_chart_specs_emit_sse_events(self):
        from expense_agent.charting import pop_pending_chart_specs, queue_pending_chart_spec
        from routes.agent import _drain_pending_chart_sse

        pop_pending_chart_specs()
        queue_pending_chart_spec({"id": "chart_nested", "title": "Nested", "option": {}})

        events = list(_drain_pending_chart_sse())

        self.assertEqual(len(events), 1)
        self.assertIn("event: chart", events[0])
        self.assertIn('"id": "chart_nested"', events[0])

    def test_stream_event_errors_are_sanitized_before_sse(self):
        from routes.agent import _safe_agent_error_message

        message = _safe_agent_error_message(
            "429 RESOURCE_EXHAUSTED. {'error': {'message': 'Quota exceeded for metric: secret-ish-provider-detail'}}",
            "mensaje",
        )

        self.assertIn("cuota", message)
        self.assertNotIn("secret-ish-provider-detail", message)


if __name__ == "__main__":
    unittest.main()
