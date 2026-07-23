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

    def test_temporary_schedule_has_a_manual_entry_point(self):
        self.assertIn("  schedule:\n", self.schedule)
        self.assertIn("  workflow_dispatch:\n", self.schedule)
        self.assertIn("uses: ./.github/workflows/update-disclosures.yml", self.schedule)
        self.assertEqual(self.schedule.count('- cron: "*/5 * * * *"'), 1)

    def test_schedule_entry_point_logs_trigger_before_update(self):
        self.assertIn('echo "event_name=${{ github.event_name }}"', self.schedule)
        self.assertIn('echo "actor=${{ github.actor }}"', self.schedule)
        self.assertIn("    needs: trigger-info\n", self.schedule)

    def test_run_name_and_trigger_diagnostics_distinguish_scheduled_runs(self):
        self.assertIn("run-name:", self.workflow)
        self.assertIn("github.event_name == 'schedule'", self.workflow)
        self.assertIn('echo "event=${{ github.event_name }}"', self.workflow)
        self.assertIn('echo "scheduled_at=${{ github.event.schedule || \'manual\' }}"', self.workflow)


if __name__ == "__main__":
    unittest.main()
