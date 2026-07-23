import unittest
from pathlib import Path


class UpdateWorkflowTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.workflow = Path(".github/workflows/update-disclosures.yml").read_text(encoding="utf-8")

    def test_manual_and_weekday_schedules_are_configured(self):
        self.assertIn("  workflow_dispatch:\n", self.workflow)
        for cron in (
            "7 0 * * 1-5",
            "7 3 * * 1-5",
            "37 6 * * 1-5",
            "37 8 * * 1-5",
        ):
            self.assertEqual(self.workflow.count(f'- cron: "{cron}"'), 1)


if __name__ == "__main__":
    unittest.main()
