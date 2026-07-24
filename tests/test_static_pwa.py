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
        self.assertIn('const CACHE = "kabu-daily-pages-v7";', self.service_worker)

    def test_update_button_waits_for_success_without_a_frontend_token(self):
        self.assertIn('id="updateButton"', self.html)
        self.assertIn('name="update-api-url" content="https://proud-wildflower-1a64.tomoya03212738.workers.dev/"', self.html)
        self.assertIn('fetch(updateApiUrl, { method: "POST" })', self.javascript)
        self.assertIn('showNotice("更新を開始しました")', self.javascript)
        self.assertIn("response.status === 405", self.javascript)
        self.assertIn('showNotice("更新中…")', self.javascript)
        self.assertIn("console.warn", self.javascript)
        self.assertIn('button.querySelector(".update-label").textContent = "更新中…"', self.javascript)
        self.assertIn('run.conclusion !== "success"', self.javascript)
        self.assertIn("window.location.reload()", self.javascript)
        self.assertNotIn("GITHUB_TOKEN", self.html + self.javascript)

    def test_update_button_has_mobile_touch_target_and_spinner(self):
        self.assertIn(".update-button", self.styles)
        self.assertIn("height:44px", self.styles)
        self.assertIn("@keyframes update-spin", self.styles)


if __name__ == "__main__":
    unittest.main()
