import unittest
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


if __name__ == "__main__":
    unittest.main()
