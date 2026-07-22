from __future__ import annotations

import argparse
import hashlib
import json
import re
import time
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import Request, urlopen

JST = timezone(timedelta(hours=9))
BASE_URL = "https://www.release.tdnet.info/inbs/"
USER_AGENT = "Kabu-Daily-GitHub-Actions/2.0 (public dashboard; low-frequency access)"
TIMEOUT_SECONDS = 20
RETENTION_DAYS = 180
MAX_ATTEMPTS = 2

CATEGORY_RULES = (
    (("優待制度の新設", "株主優待制度の導入", "株主優待制度を新設"), "優待新設", 5),
    (("優待制度の拡充", "株主優待制度の拡充"), "優待拡充", 4),
    (("優待制度の廃止", "株主優待制度廃止"), "優待廃止", 5),
    (("優待制度の変更", "株主優待制度の変更"), "優待変更", 3),
    (("増配", "記念配当"), "増配", 4),
    (("減配", "無配"), "減配", 5),
    (("配当予想の修正", "剰余金の配当"), "配当予想修正", 3),
    (("自己株式の取得", "自社株買い"), "自社株買い", 4),
    (("公開買付", "ＴＯＢ", "TOB", "合併", "株式交換", "買収"), "TOB・M&A", 5),
    (("業績予想の修正", "上方修正", "下方修正"), "業績予想修正", 4),
    (("決算短信", "決算説明"), "決算", 3),
)


def classify(title: str) -> tuple[str, int]:
    normalized = title.casefold()
    for keywords, category, importance in CATEGORY_RULES:
        if any(keyword.casefold() in normalized for keyword in keywords):
            return category, importance
    return "その他", 2


class TdnetParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.rows: list[tuple[list[str], list[str]]] = []
        self.cells: list[str] | None = None
        self.cell: list[str] | None = None
        self.links: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if tag == "tr":
            self.cells, self.links = [], []
        elif tag in ("td", "th") and self.cells is not None:
            self.cell = []
        elif tag == "a" and self.cells is not None and attributes.get("href"):
            self.links.append(urljoin(BASE_URL, attributes["href"] or ""))

    def handle_data(self, data: str) -> None:
        if self.cell is not None:
            self.cell.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag in ("td", "th") and self.cell is not None and self.cells is not None:
            self.cells.append(" ".join("".join(self.cell).split()))
            self.cell = None
        elif tag == "tr" and self.cells is not None:
            self.rows.append((self.cells, self.links))
            self.cells = None


def disclosure_id(source_url: str) -> str:
    return hashlib.sha256(source_url.encode()).hexdigest()[:20]


def parse(html: str, date: str) -> list[dict[str, object]]:
    parser = TdnetParser()
    parser.feed(html)
    disclosures = []
    for cells, links in parser.rows:
        pdf_url = next((link for link in links if ".pdf" in link.lower()), "")
        if len(cells) < 4 or not pdf_url or not re.fullmatch(r"\d{2}:\d{2}", cells[0]):
            continue
        code_index = next((index for index, value in enumerate(cells) if re.fullmatch(r"\d{4,5}", value)), -1)
        if code_index < 0 or len(cells) <= code_index + 2:
            continue
        title = cells[code_index + 2]
        category, importance = classify(title)
        disclosures.append({
            "id": disclosure_id(pdf_url), "published_at": f"{date}T{cells[0]}:00+09:00",
            "security_code": cells[code_index][:4], "company_name": cells[code_index + 1],
            "title": title, "category": category, "importance": importance, "pdf_url": pdf_url,
        })
    return disclosures


def download(url: str) -> tuple[bytes, str | None]:
    request = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "text/html", "Accept-Language": "ja"})
    for attempt in range(MAX_ATTEMPTS):
        try:
            with urlopen(request, timeout=TIMEOUT_SECONDS) as response:
                return response.read(), response.headers.get_content_charset()
        except HTTPError as error:
            if error.code < 500 or attempt + 1 == MAX_ATTEMPTS:
                raise
        except (URLError, TimeoutError):
            if attempt + 1 == MAX_ATTEMPTS:
                raise
        time.sleep(3)
    raise RuntimeError("TDnetから応答がありません")


def fetch(date: datetime) -> list[dict[str, object]]:
    date_text = date.strftime("%Y-%m-%d")
    url = f"{BASE_URL}I_list_001_{date.strftime('%Y%m%d')}.html"
    raw, declared_charset = download(url)
    for charset in (declared_charset, "utf-8", "cp932"):
        if not charset:
            continue
        try:
            return parse(raw.decode(charset), date_text)
        except (UnicodeDecodeError, LookupError):
            pass
    return parse(raw.decode("utf-8", errors="replace"), date_text)


def read_json(path: Path, default: dict[str, object]) -> dict[str, object]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def write_json(path: Path, value: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def update(data_path: Path, status_path: Path, now: datetime | None = None) -> bool:
    now = now or datetime.now(JST)
    existing = read_json(data_path, {"sample": False, "disclosures": []})
    try:
        fetched = fetch(now)
        previous_items = [] if existing.get("sample") else existing.get("disclosures", [])
        by_id = {item["id"]: item for item in previous_items if isinstance(item, dict)}
        by_id.update({item["id"]: item for item in fetched})
        cutoff = now - timedelta(days=RETENTION_DAYS)
        retained = [item for item in by_id.values() if datetime.fromisoformat(str(item["published_at"])) >= cutoff]
        retained.sort(key=lambda item: str(item["published_at"]), reverse=True)
        write_json(data_path, {"sample": False, "last_success_at": now.isoformat(timespec="seconds"), "disclosures": retained})
        write_json(status_path, {"ok": True, "checked_at": now.isoformat(timespec="seconds"), "fetched_count": len(fetched), "message": "取得に成功しました"})
        return True
    except Exception as error:
        # disclosures.json は一切書き換えず、直前の正常データを保護します。
        write_json(status_path, {"ok": False, "checked_at": now.isoformat(timespec="seconds"), "fetched_count": 0,
                                 "message": "TDnetから取得できませんでした。前回のデータを表示しています。",
                                 "error_type": type(error).__name__})
        print(f"::warning::TDnet update failed: {type(error).__name__}: {error}")
        return False


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, default=Path("docs/data/disclosures.json"))
    parser.add_argument("--status", type=Path, default=Path("docs/data/status.json"))
    args = parser.parse_args()
    # 失敗状態もstatus.jsonへ保存するため、意図的に終了コードは0とします。
    update(args.data, args.status)


if __name__ == "__main__":
    main()
