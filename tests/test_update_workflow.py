import unittest
from pathlib import Path


class UpdateWorkflowTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.workflow = Path(".github/workflows/update-disclosures.yml").read_text(encoding="utf-8")
        cls.schedule = Path(".github/workflows/schedule-disclosures.yml").read_text(encoding="utf-8")

    def test_manual_worker_is_reusable(self):
        self.assertIn("  workflow_dispatch:\n", self.workflow)
        self.assertIn("  workflow_call:\n", self.workflow)
        self.assertNotIn("  schedule:\n", self.workflow)

    def test_temporary_schedule_and_manual_trigger_have_a_dedicated_entry_point(self):
        self.assertIn("  workflow_dispatch:\n", self.schedule)
        self.assertIn("  schedule:\n", self.schedule)
        for cron in ('7 0 * * 1-5', '7 3 * * 1-5', '37 6 * * 1-5', '37 8 * * 1-5'):
            self.assertEqual(self.schedule.count(f'- cron: "{cron}"'), 1)
        self.assertIn("uses: ./.github/workflows/update-disclosures.yml", self.schedule)

    def test_worker_dispatch_can_be_correlated_to_its_run(self):
        worker = Path("worker/src/index.js").read_text(encoding="utf-8")
        self.assertIn('const WORKFLOW = "schedule-disclosures.yml"', worker)
        self.assertIn("workflow_dispatch", worker)
        self.assertIn("request_id", worker)
        self.assertIn("GITHUB_TOKEN", worker)
        self.assertIn("run_id", worker)
        self.assertIn("env.GITHUB_REF", worker)
        self.assertIn('url.pathname === "/health"', worker)
        self.assertIn('code: "method_not_allowed"', worker)
        self.assertIn("inputs.request_id", self.schedule)

    def test_scheduled_entry_point_logs_trigger_before_update(self):
        self.assertIn("  trigger-info:\n", self.schedule)
        self.assertIn('echo "event_name=${{ github.event_name }}"', self.schedule)
        self.assertIn('echo "actor=${{ github.actor }}"', self.schedule)
        self.assertIn("    needs: trigger-info\n", self.schedule)

    def test_run_name_and_trigger_diagnostics_distinguish_scheduled_runs(self):
        self.assertIn("run-name:", self.workflow)
        self.assertIn("github.event_name == 'schedule'", self.workflow)
        self.assertIn('echo "event=${{ github.event_name }}"', self.workflow)
        self.assertIn('echo "scheduled_at=${{ github.event.schedule || \'manual\' }}"', self.workflow)

    def test_gemini_key_is_only_passed_as_a_secret(self):
        self.assertIn("GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}", self.workflow)
        self.assertIn("GEMINI_SUMMARY_LIMIT: \"3\"", self.workflow)
        self.assertIn("    secrets: inherit", self.schedule)

    def test_tdnet_fetch_runs_as_a_package_module(self):
        self.assertIn("run: python -m scripts.fetch_tdnet", self.workflow)


if __name__ == "__main__":
    unittest.main()
