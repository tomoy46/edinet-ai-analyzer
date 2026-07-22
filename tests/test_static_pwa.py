import unittest
import re
from pathlib import Path


class StaticPwaTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = Path("docs/index.html").read_text(encoding="utf-8")
        cls.javascript = Path("docs/app.js").read_text(encoding="utf-8")
        cls.styles = Path("docs/styles.css").read_text(encoding="utf-8")

    def test_quick_filters_are_present(self):
        for element_id in (
            "todayOnly", "unreadOnly", "savedOnly", "importantOnly", "benefitOnly",
            "dividendOnly", "earningsOnly", "maOnly",
        ):
            self.assertIn(f'id="{element_id}"', self.html)

    def test_all_sort_orders_are_present(self):
        for value in ("newest", "oldest", "importance", "company", "code"):
            self.assertIn(f'value="{value}"', self.html)

    def test_read_state_is_persisted_locally(self):
        self.assertIn('localStorage.getItem("readDisclosures")', self.javascript)
        self.assertIn('localStorage.setItem("readDisclosures"', self.javascript)
        self.assertIn('id="markAllRead"', self.html)
        self.assertIn('id="resetRead"', self.html)

    def test_importance_has_five_color_levels(self):
        for importance in range(1, 6):
            self.assertIn(f".importance-{importance}", self.styles)

    def test_javascript_references_existing_elements(self):
        """Prevent a missing element from stopping rendering after a successful fetch."""
        referenced_ids = set(re.findall(r'\$\("#([A-Za-z][A-Za-z0-9_-]*)"\)', self.javascript))
        html_ids = set(re.findall(r'id="([A-Za-z][A-Za-z0-9_-]*)"', self.html))
        self.assertEqual(referenced_ids - html_ids, set())

    def test_null_initial_update_time_is_supported(self):
        self.assertIn('if (!value) return "未取得"', self.javascript)
        self.assertIn("data.sample === true", self.javascript)

    def test_data_urls_are_based_on_app_location(self):
        self.assertIn('new URL("./", APP_SCRIPT_URL)', self.javascript)
        self.assertIn('new URL("data/disclosures.json", APP_BASE_URL)', self.javascript)
        self.assertIn('new URL("data/status.json", APP_BASE_URL)', self.javascript)
        self.assertNotIn('fetch("/data/', self.javascript)


if __name__ == "__main__":
    unittest.main()
