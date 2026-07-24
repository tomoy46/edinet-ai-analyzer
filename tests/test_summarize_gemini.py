import json
import os
import unittest
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError

from scripts.summarize_gemini import (
    DEFAULT_SUMMARY_LIMIT,
    GEMINI_DISCLOSURE_INTERVAL_SECONDS,
    GEMINI_MAX_ATTEMPTS,
    GEMINI_MODEL,
    GEMINI_RETRY_DELAYS,
    add_missing_summaries,
    generate_summary,
    should_summarize,
)


class GeminiSummaryTest(unittest.TestCase):
    def test_free_tier_defaults(self):
        self.assertEqual(DEFAULT_SUMMARY_LIMIT, 3)
        self.assertEqual(GEMINI_MODEL, "gemini-2.5-flash")
        self.assertEqual(GEMINI_MAX_ATTEMPTS, 4)
        self.assertEqual(GEMINI_RETRY_DELAYS, (30, 60, 120))

    def test_only_requested_disclosures_are_candidates(self):
        self.assertTrue(should_summarize({"importance": 4, "category": "TOB"}))
        self.assertTrue(should_summarize({"importance": 3, "category": "決算"}))
        self.assertTrue(should_summarize({"importance": 1, "category": "優待廃止"}))
        self.assertFalse(should_summarize({"importance": 3, "category": "優待拡充"}))
        self.assertFalse(should_summarize({"importance": 1, "category": "その他"}))

    @patch("scripts.summarize_gemini.generate_summary")
    def test_limit_and_existing_summary_reuse(self, generate):
        generate.return_value = {"summary": ["x"]}
        items = [
            {"id": "cached", "importance": 5, "ai_summary": {"summary": ["cached"]}},
            {"id": "one", "importance": 5},
            {"id": "two", "importance": 5},
        ]
        with patch.dict(os.environ, {"GEMINI_API_KEY": "secret", "GEMINI_SUMMARY_LIMIT": "1"}):
            self.assertEqual(add_missing_summaries(items), 1)
        self.assertEqual(generate.call_count, 1)
        self.assertEqual(items[0]["ai_summary"], {"summary": ["cached"]})
        self.assertNotIn("ai_summary", items[2])

    @patch("scripts.summarize_gemini.time.sleep")
    @patch("scripts.summarize_gemini._download_pdf", return_value=b"pdf")
    @patch("scripts.summarize_gemini.urlopen")
    def test_429_is_retried_and_key_uses_header(self, urlopen, _download, sleep):
        error = HTTPError("url", 429, "limited", {"Retry-After": "45"}, None)
        response = MagicMock()
        response.__enter__.return_value.read.return_value = json.dumps({
            "candidates": [{"content": {"parts": [{"text": json.dumps({
                "summary": ["要約"], "impact": "中立", "key_points": ["要点"], "caution": "注意"
            }, ensure_ascii=False)}]}}]
        }, ensure_ascii=False).encode()
        urlopen.side_effect = [error, response]
        result = generate_summary({"pdf_url": "https://example.com/a.pdf", "id": "a"}, "top-secret")
        self.assertEqual(result["model"], GEMINI_MODEL)
        self.assertEqual(urlopen.call_count, 2)
        self.assertEqual(sleep.call_count, 1)
        sleep.assert_called_once_with(45.0)
        request = urlopen.call_args_list[0].args[0]
        self.assertEqual(request.get_header("X-goog-api-key"), "top-secret")
        self.assertNotIn("top-secret", request.full_url)

    @patch("scripts.summarize_gemini.time.sleep")
    @patch("scripts.summarize_gemini._download_pdf", return_value=b"pdf")
    @patch("scripts.summarize_gemini.urlopen")
    def test_persistent_429_uses_exponential_backoff_then_skips(self, urlopen, _download, sleep):
        urlopen.side_effect = [HTTPError("url", 429, "limited", {}, None) for _ in range(4)]
        rate_limits = MagicMock()
        with self.assertRaises(HTTPError):
            generate_summary({"pdf_url": "https://example.com/a.pdf"}, "secret", rate_limits)
        self.assertEqual(urlopen.call_count, 4)
        self.assertEqual([call.args[0] for call in sleep.call_args_list], [30.0, 60.0, 120.0])
        self.assertEqual(rate_limits.call_count, 4)

    @patch("scripts.summarize_gemini.time.sleep")
    @patch("scripts.summarize_gemini.generate_summary")
    def test_disclosures_are_spaced_and_results_are_logged(self, generate, sleep):
        def summarize(item, _key, on_rate_limit):
            if item["id"] == "two":
                on_rate_limit()
                raise HTTPError("url", 429, "limited", {}, None)
            return {"summary": ["ok"]}

        generate.side_effect = summarize
        items = [{"id": value, "importance": 5} for value in ("one", "two", "three", "four")]
        with patch.dict(os.environ, {"GEMINI_API_KEY": "secret"}, clear=True), patch("builtins.print") as output:
            self.assertEqual(add_missing_summaries(items), 2)
        self.assertEqual(generate.call_count, 3)
        self.assertEqual([call.args[0] for call in sleep.call_args_list], [GEMINI_DISCLOSURE_INTERVAL_SECONDS] * 2)
        output.assert_any_call("AI summary results: success=2 failed=1 rate_limited_429=1")
        self.assertNotIn("ai_summary", items[1])
        self.assertNotIn("ai_summary", items[3])

    @patch("scripts.summarize_gemini.time.sleep")
    @patch("scripts.summarize_gemini._download_pdf", return_value=b"pdf")
    @patch("scripts.summarize_gemini.urlopen")
    def test_non_retryable_error_is_not_retried(self, urlopen, _download, sleep):
        urlopen.side_effect = HTTPError("url", 400, "bad", {}, None)
        with self.assertRaises(HTTPError):
            generate_summary({"pdf_url": "https://example.com/a.pdf"}, "secret")
        self.assertEqual(urlopen.call_count, 1)
        sleep.assert_not_called()


if __name__ == "__main__":
    unittest.main()
