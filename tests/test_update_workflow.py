import unittest
from pathlib import Path


class UpdateWorkflowTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.workflow = Path(".github/workflows/update-disclosures.yml").read_text(encoding="utf-8")

    def test_manual_trigger_and_staggered_weekday_schedules(self):
        self.assertIn("  workflow_dispatch:\n", self.workflow)
        expected_crons = (
            "7 0 * * 1-5",
            "7 3 * * 1-5",
            "37 6 * * 1-5",
            "37 8 * * 1-5",
        )
        for cron in expected_crons:
            self.assertEqual(self.workflow.count(f'- cron: "{cron}"'), 1)

        self.assertEqual(self.workflow.count("    - cron:"), len(expected_crons))


if __name__ == "__main__":
    unittest.main()
