import unittest
from pathlib import Path


class StaticPwaTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = Path("docs/index.html").read_text(encoding="utf-8")
        cls.javascript = Path("docs/app.js").read_text(encoding="utf-8")
        cls.service_worker = Path("docs/sw.js").read_text(encoding="utf-8")
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

    def test_data_urls_are_resolved_from_app_script(self):
        self.assertIn("document.currentScript.src", self.javascript)
        self.assertIn('new URL("data/disclosures.json", basePath)', self.javascript)
        self.assertIn('new URL("data/status.json", basePath)', self.javascript)
        self.assertNotIn('fetch("data/', self.javascript)

    def test_removed_fetched_count_is_not_referenced(self):
        self.assertNotIn("fetchedCount", self.javascript)

    def test_service_worker_cache_version_is_updated(self):
        self.assertIn('const CACHE = "kabu-daily-pages-v4";', self.service_worker)


if __name__ == "__main__":
    unittest.main()
