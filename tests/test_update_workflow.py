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

    def test_weekday_schedules_have_a_dedicated_entry_point(self):
        self.assertIn("  schedule:\n", self.schedule)
        self.assertIn("uses: ./.github/workflows/update-disclosures.yml", self.schedule)
        for cron in (
            "7 0 * * 1-5",
            "7 3 * * 1-5",
            "37 6 * * 1-5",
            "37 8 * * 1-5",
        ):
            self.assertEqual(self.schedule.count(f'- cron: "{cron}"'), 1)

    def test_run_name_and_trigger_diagnostics_distinguish_scheduled_runs(self):
        self.assertIn("run-name:", self.workflow)
        self.assertIn("github.event_name == 'schedule'", self.workflow)
        self.assertIn('echo "event=${{ github.event_name }}"', self.workflow)
        self.assertIn('echo "scheduled_at=${{ github.event.schedule || \'manual\' }}"', self.workflow)


if __name__ == "__main__":
    unittest.main()
