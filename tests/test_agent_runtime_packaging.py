from pathlib import Path
import importlib
import shutil
import subprocess
import sys
import tempfile
import unittest


class AgentRuntimePackagingTest(unittest.TestCase):
    def test_agent_runtime_exports_root_agent_without_api_runtime_imports(self):
        before_modules = set(sys.modules)
        module = importlib.import_module("agent_runtime.agent")
        imported_by_wrapper = set(sys.modules) - before_modules

        self.assertTrue(hasattr(module, "root_agent"))
        self.assertEqual(module.root_agent.name, "expense_agent")

        wrapper_source = Path("agent_runtime/agent.py").read_text()
        self.assertNotIn("routes", wrapper_source)
        self.assertNotIn("FastAPI", wrapper_source)
        self.assertNotIn("main", wrapper_source)

        self.assertNotIn("routes.agent", imported_by_wrapper)
        self.assertNotIn("main", imported_by_wrapper)

    def test_agent_runtime_requirements_are_agent_only(self):
        requirements = Path("agent_runtime/requirements.txt").read_text()

        expected = {
            "motor>=3.7.0",
            "python-dotenv>=1.0.0",
            "certifi>=2024.0.0",
            "google-adk==2.1.0",
            "google-genai>=1.0.0",
            "httpx>=0.27.0",
            "mcp>=1.0.0",
            "openpyxl>=3.1.0",
        }
        self.assertEqual(set(requirements.splitlines()), expected)
        self.assertNotIn("fastapi", requirements.lower())
        self.assertNotIn("uvicorn", requirements.lower())

    def test_agent_runtime_staging_metadata_is_present(self):
        ae_ignore = Path("agent_runtime/.ae_ignore")
        self.assertTrue(ae_ignore.exists())
        self.assertIn("__pycache__", ae_ignore.read_text())
        self.assertTrue(Path("agent_runtime/expense_agent").is_symlink())
        self.assertTrue(Path("agent_runtime/db").is_symlink())

    def test_agent_runtime_imports_from_isolated_staged_copy(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            staged_parent = Path(tmpdir)
            staged_agent = staged_parent / "expense_agent_tmp"
            shutil.copytree("agent_runtime", staged_agent, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))

            repo_root = str(Path.cwd())
            script = (
                "import sys; "
                f"sys.path[:] = [{str(staged_parent)!r}] + [p for p in sys.path if p and p != {repo_root!r}]; "
                "from expense_agent_tmp.agent import root_agent; "
                "print(root_agent.name)"
            )
            result = subprocess.run(
                [sys.executable, "-c", script],
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("expense_agent", result.stdout)


if __name__ == "__main__":
    unittest.main()
