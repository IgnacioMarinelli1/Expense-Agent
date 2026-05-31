from pathlib import Path
import unittest


class WhatsappRemovalTest(unittest.TestCase):
    def test_fastapi_app_does_not_mount_whatsapp_router(self):
        main_source = Path("main.py").read_text()

        self.assertNotIn("routes.whatsapp", main_source)
        self.assertNotIn("whatsapp_router", main_source)

    def test_twilio_is_not_a_runtime_dependency(self):
        requirements = Path("requirements.txt").read_text()

        self.assertNotIn("twilio", requirements.lower())

    def test_payment_model_does_not_expose_whatsapp_input_method(self):
        payment_model = Path("models/payment.py").read_text()
        schema = Path("db/schema.py").read_text()

        self.assertNotIn('"whatsapp"', payment_model)
        self.assertNotIn("'whatsapp'", schema)

    def test_project_docs_do_not_advertise_whatsapp_channel(self):
        context = Path("context.md").read_text()

        self.assertNotIn("Twilio", context)
        self.assertNotIn("WhatsApp", context)
        self.assertNotIn("/whatsapp/webhook", context)


if __name__ == "__main__":
    unittest.main()
