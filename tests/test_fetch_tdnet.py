import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError, URLError

from scripts.fetch_tdnet import JST, MAX_ATTEMPTS, classify, disclosure_id, download, parse, update


class FetchTdnetTest(unittest.TestCase):
    def test_required_categories(self):
        cases = {
            "株主優待制度の新設": "優待新設", "株主優待制度の拡充": "優待拡充",
            "株主優待制度の変更": "優待変更", "株主優待制度の廃止": "優待廃止",
            "配当予想の修正（増配）": "増配", "配当予想の修正（減配）": "減配",
            "配当予想の修正": "その他", "自己株式の取得": "自社株買い",
            "決算短信": "決算", "業績予想の修正": "業績予想修正",
            "公開買付けのお知らせ": "TOB", "株式交換のお知らせ": "M&A",
            "代表者の異動": "その他",
        }
        for title, expected in cases.items():
            with self.subTest(title=title):
                self.assertEqual(classify(title)[0], expected)

    def test_importance_is_always_between_one_and_five(self):
        titles = ["株主優待制度の新設", "決算短信", "代表者の異動"]
        for title in titles:
            self.assertIn(classify(title)[1], range(1, 6))
        self.assertEqual(classify("代表者の異動")[1], 1)
        self.assertEqual(classify("株主優待制度の新設")[1], 5)

    def test_parse_tdnet_row(self):
        html = '<table><tr><td>15:30</td><td>7203</td><td>トヨタ</td><td><a href="x.pdf">自己株式の取得</a></td></tr></table>'
        item = parse(html, "2026-07-22")[0]
        self.assertEqual(item["security_code"], "7203")
        self.assertEqual(item["category"], "自社株買い")
        self.assertEqual(item["id"], disclosure_id("https://www.release.tdnet.info/inbs/x.pdf"))

    @patch("scripts.fetch_tdnet.urlopen")
    def test_403_is_not_retried(self, urlopen):
        urlopen.side_effect = HTTPError("url", 403, "Forbidden", {}, None)
        with self.assertRaises(HTTPError):
            download("https://example.com")
        self.assertEqual(urlopen.call_count, 1)

    @patch("scripts.fetch_tdnet.time.sleep")
    @patch("scripts.fetch_tdnet.urlopen")
    def test_network_retry_is_limited(self, urlopen, _sleep):
        urlopen.side_effect = URLError("offline")
        with self.assertRaises(URLError):
            download("https://example.com")
        self.assertEqual(urlopen.call_count, MAX_ATTEMPTS)

    def test_failure_preserves_previous_data(self):
        with tempfile.TemporaryDirectory() as directory:
            data = Path(directory) / "disclosures.json"; status = Path(directory) / "status.json"
            original = {"sample": False, "last_success_at": "2026-07-21T12:00:00+09:00", "disclosures": [{"id": "old"}]}
            data.write_text(json.dumps(original), encoding="utf-8")
            with patch("scripts.fetch_tdnet.fetch", side_effect=URLError("offline")):
                self.assertFalse(update(data, status, datetime(2026, 7, 22, 12, tzinfo=JST)))
            self.assertEqual(json.loads(data.read_text()), original)
            self.assertFalse(json.loads(status.read_text())["ok"])

    def test_success_replaces_sample_and_removes_duplicates(self):
        with tempfile.TemporaryDirectory() as directory:
            data = Path(directory) / "disclosures.json"; status = Path(directory) / "status.json"
            data.write_text(json.dumps({"sample": True, "disclosures": [{"id": "sample"}]}), encoding="utf-8")
            item = {"id": "real", "published_at": "2026-07-22T10:00:00+09:00"}
            with patch("scripts.fetch_tdnet.fetch", return_value=[item, item]):
                self.assertTrue(update(data, status, datetime(2026, 7, 22, 12, tzinfo=JST)))
            result = json.loads(data.read_text())
            self.assertFalse(result["sample"])
            self.assertEqual(result["disclosures"], [item])

    @patch("scripts.fetch_tdnet.add_missing_summaries", return_value=0)
    def test_existing_ai_summary_is_reused(self, summarize):
        with tempfile.TemporaryDirectory() as directory:
            data = Path(directory) / "disclosures.json"; status = Path(directory) / "status.json"
            cached = {"summary": ["前回の要約"], "impact": "中立", "key_points": [], "caution": "注意"}
            old = {"id": "same", "published_at": "2026-07-22T10:00:00+09:00", "ai_summary": cached}
            fresh = {"id": "same", "published_at": "2026-07-22T10:00:00+09:00", "title": "updated"}
            data.write_text(json.dumps({"sample": False, "disclosures": [old]}), encoding="utf-8")
            with patch("scripts.fetch_tdnet.fetch", return_value=[fresh]):
                self.assertTrue(update(data, status, datetime(2026, 7, 22, 12, tzinfo=JST)))
            self.assertEqual(json.loads(data.read_text())["disclosures"][0]["ai_summary"], cached)
            summarize.assert_called_once()


if __name__ == "__main__":
    unittest.main()
