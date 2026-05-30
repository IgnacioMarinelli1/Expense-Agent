from pathlib import Path
import unittest


class FrontendApiParamsTest(unittest.TestCase):
    def test_frontend_uses_backend_month_query_param(self):
        client = Path("frontend/src/lib/api/client.ts").read_text()

        self.assertIn("?month=${mes}", client)
        self.assertNotIn("?mes=${mes}", client)

    def test_frontend_audio_client_matches_backend_response_key(self):
        client = Path("frontend/src/lib/api/client.ts").read_text()

        self.assertIn("Promise<{ response: string }>", client)
        self.assertNotIn("Promise<{ respuesta: string }>", client)

    def test_frontend_stream_and_message_support_charts(self):
        client = Path("frontend/src/lib/api/client.ts").read_text()
        store = Path("frontend/src/lib/stores/expenses.ts").read_text()
        page = Path("frontend/src/routes/+page.svelte").read_text()

        self.assertIn("onChart?: (chart: ChartSpec) => void", client)
        self.assertIn("if (event === 'chart') handlers.onChart?.(data)", client)
        self.assertIn("export type ChartSpec", store)
        self.assertIn("charts?: ChartSpec[]", store)
        self.assertIn("ChatChart", page)

    def test_frontend_declares_echarts_dependencies(self):
        package_json = Path("frontend/package.json").read_text()

        self.assertIn('"echarts"', package_json)
        self.assertIn('"echarts-gl"', package_json)


if __name__ == "__main__":
    unittest.main()
