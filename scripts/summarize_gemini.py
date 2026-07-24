from __future__ import annotations

import base64
import json
import os
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

GEMINI_MODEL = "gemini-2.5-flash"
GEMINI_API_BASE = "https://generativelanguage.googleapis.com"
# Gemini 2.5 の公式 REST API は v1beta を正規の呼び出し先として案内しています。
GEMINI_API_VERSION = "v1beta"
GEMINI_ENDPOINT = f"{GEMINI_API_BASE}/{GEMINI_API_VERSION}/models/{GEMINI_MODEL}:generateContent"
GEMINI_TIMEOUT_SECONDS = 60
GEMINI_MAX_RETRIES = 3
GEMINI_MAX_ATTEMPTS = GEMINI_MAX_RETRIES + 1
GEMINI_RETRY_DELAYS = (30, 60, 120)
GEMINI_DISCLOSURE_INTERVAL_SECONDS = 15
DEFAULT_SUMMARY_LIMIT = 3
SUMMARY_CATEGORIES = frozenset({"決算", "業績予想修正", "増配", "減配", "優待新設", "優待廃止", "自社株買い"})
SUMMARY_SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {"type": "array", "items": {"type": "string"}, "maxItems": 3},
        "impact": {"type": "string", "enum": ["プラス", "中立", "マイナス"]},
        "key_points": {"type": "array", "items": {"type": "string"}, "maxItems": 3},
        "caution": {"type": "string"},
    },
    "required": ["summary", "impact", "key_points", "caution"],
    "additionalProperties": False,
}


def should_summarize(item: dict[str, object]) -> bool:
    return int(item.get("importance", 0)) >= 4 or item.get("category") in SUMMARY_CATEGORIES


def _summary_limit() -> int:
    try:
        return max(0, int(os.environ.get("GEMINI_SUMMARY_LIMIT", DEFAULT_SUMMARY_LIMIT)))
    except ValueError:
        return DEFAULT_SUMMARY_LIMIT


def _download_pdf(url: str) -> bytes:
    request = Request(url, headers={"User-Agent": "Kabu-Daily-GitHub-Actions/2.0", "Accept": "application/pdf"})
    with urlopen(request, timeout=GEMINI_TIMEOUT_SECONDS) as response:
        return response.read()


def _validate_summary(value: object) -> dict[str, object]:
    if not isinstance(value, dict):
        raise ValueError("Gemini response is not an object")
    summary = value.get("summary")
    points = value.get("key_points")
    impact = value.get("impact")
    caution = value.get("caution")
    if not isinstance(summary, list) or not 1 <= len(summary) <= 3 or not all(isinstance(x, str) and x.strip() for x in summary):
        raise ValueError("invalid summary")
    if not isinstance(points, list) or len(points) > 3 or not all(isinstance(x, str) and x.strip() for x in points):
        raise ValueError("invalid key points")
    if impact not in ("プラス", "中立", "マイナス") or not isinstance(caution, str):
        raise ValueError("invalid impact or caution")
    return {"summary": summary, "impact": impact, "key_points": points, "caution": caution.strip(), "model": GEMINI_MODEL}


def _retry_after_seconds(error: HTTPError, fallback: int) -> float:
    value = error.headers.get("Retry-After") if error.headers else None
    try:
        return max(0.0, float(value)) if value is not None else float(fallback)
    except (TypeError, ValueError):
        return float(fallback)


def _safe_error_body(error: HTTPError, api_key: str, pdf: bytes) -> str:
    """Return a bounded Gemini error response with request secrets removed."""
    try:
        body = error.read().decode("utf-8", errors="replace")
    except (AttributeError, OSError):
        return "<response body unavailable>"
    # Google error responses do not normally echo request data, but redact both
    # secrets explicitly before the response is allowed to reach Actions logs.
    for secret in (api_key, base64.b64encode(pdf).decode("ascii")):
        if secret:
            body = body.replace(secret, "[REDACTED]")
    return " ".join(body.split())[:4000] or "<empty response body>"


def generate_summary(item: dict[str, object], api_key: str, on_rate_limit=None) -> dict[str, object]:
    pdf = _download_pdf(str(item["pdf_url"]))
    payload = {
        "contents": [{"parts": [
            {"text": (
                "この適時開示PDFを日本語で簡潔かつ客観的に要約してください。推測を避け、数値・条件・時期を優先してください。"
                "summaryは1要素を1行として最大3件、key_pointsは最大3件、cautionは投資判断上の注意点です。"
                "株価へのimpactは開示内容のみからプラス・中立・マイナスのいずれかを選んでください。"
                f"\n会社: {item.get('company_name', '')}\n表題: {item.get('title', '')}"
            )},
            {"inlineData": {"mimeType": "application/pdf", "data": base64.b64encode(pdf).decode("ascii")}},
        ]}],
        "generationConfig": {"temperature": 0.1, "responseMimeType": "application/json", "responseJsonSchema": SUMMARY_SCHEMA},
    }
    request = Request(
        GEMINI_ENDPOINT,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json", "x-goog-api-key": api_key},
        method="POST",
    )
    for attempt in range(GEMINI_MAX_ATTEMPTS):
        try:
            with urlopen(request, timeout=GEMINI_TIMEOUT_SECONDS) as response:
                result = json.loads(response.read().decode("utf-8"))
            text = result["candidates"][0]["content"]["parts"][0]["text"]
            return _validate_summary(json.loads(text))
        except HTTPError as error:
            # Only errors raised by the Gemini request reach this block; PDF
            # download errors happen before the request/retry loop.
            if error.code == 404:
                error.gemini_response_body = _safe_error_body(error, api_key, pdf)
            if error.code == 429:
                if on_rate_limit:
                    on_rate_limit()
                if attempt + 1 == GEMINI_MAX_ATTEMPTS:
                    raise
                time.sleep(_retry_after_seconds(error, GEMINI_RETRY_DELAYS[attempt]))
                continue
            if not 500 <= error.code < 600 or attempt + 1 == GEMINI_MAX_ATTEMPTS:
                raise
        except (URLError, TimeoutError):
            if attempt + 1 == GEMINI_MAX_ATTEMPTS:
                raise
        time.sleep(2 ** (attempt + 1))
    raise RuntimeError("Gemini API did not respond")


def add_missing_summaries(items: list[dict[str, object]]) -> int:
    api_key = os.environ.get("GEMINI_API_KEY", "")
    limit = _summary_limit()
    if not api_key or limit == 0:
        print("AI summary results: success=0 failed=0 rate_limited_429=0")
        return 0
    candidates = [item for item in items if should_summarize(item) and not item.get("ai_summary")][:limit]
    completed = 0
    failed = 0
    rate_limited = 0
    for index, item in enumerate(candidates):
        if index:
            time.sleep(GEMINI_DISCLOSURE_INTERVAL_SECONDS)
        hit_rate_limit = False

        def record_rate_limit() -> None:
            nonlocal hit_rate_limit
            hit_rate_limit = True

        try:
            item["ai_summary"] = generate_summary(item, api_key, on_rate_limit=record_rate_limit)
            completed += 1
        except Exception as error:
            failed += 1
            if isinstance(error, HTTPError) and error.code == 429:
                hit_rate_limit = True
            # APIキーやPDF本文は出力せず、通常のTDnet更新を継続します。
            status = f" HTTP {error.code}" if isinstance(error, HTTPError) else ""
            print(f"::warning::AI summary skipped for disclosure {item.get('id', 'unknown')} ({type(error).__name__}{status})")
            if isinstance(error, HTTPError) and error.code == 404 and hasattr(error, "gemini_response_body"):
                print(f"::warning::Gemini API HTTP 404 response: {error.gemini_response_body}")
        if hit_rate_limit:
            rate_limited += 1
    print(f"AI summary results: success={completed} failed={failed} rate_limited_429={rate_limited}")
    return completed
