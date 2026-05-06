from __future__ import annotations

import csv
import json
import re
from collections.abc import Iterable
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

import requests


@dataclass(frozen=True)
class Gift:
    name: str
    price: int
    image_url: str | None


class _GiftParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._in_gift = False
        self._in_name = False
        self._in_price = False
        self._cur_img: str | None = None
        self._cur_name_parts: list[str] = []
        self._cur_price_parts: list[str] = []
        self.gifts: list[Gift] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        a = dict(attrs)
        if tag == "div" and a.get("class") == "gift":
            self._in_gift = True
            self._cur_img = None
            self._cur_name_parts = []
            self._cur_price_parts = []
            return

        if not self._in_gift:
            return

        if tag == "img" and self._cur_img is None:
            src = a.get("src")
            if src:
                self._cur_img = src
        elif tag == "p" and a.get("class") == "gift-name":
            self._in_name = True
        elif tag == "p" and a.get("class") == "gift-price":
            self._in_price = True

    def handle_endtag(self, tag: str) -> None:
        if not self._in_gift:
            return

        if tag == "p":
            self._in_name = False
            self._in_price = False
        elif tag == "div":
            # Close of the gift card.
            name = re.sub(r"\s+", " ", "".join(self._cur_name_parts)).strip()
            price_txt = re.sub(r"\s+", " ", "".join(self._cur_price_parts)).strip()
            if name and price_txt.isdigit():
                self.gifts.append(Gift(name=name, price=int(price_txt), image_url=self._cur_img))
            self._in_gift = False
            self._in_name = False
            self._in_price = False

    def handle_data(self, data: str) -> None:
        if not self._in_gift:
            return
        if self._in_name:
            self._cur_name_parts.append(data)
        elif self._in_price:
            self._cur_price_parts.append(data)


def _iter_urls(obj: Any) -> Iterable[str]:
    if isinstance(obj, dict):
        for v in obj.values():
            yield from _iter_urls(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _iter_urls(v)
    elif isinstance(obj, str) and obj.startswith(("http://", "https://")):
        yield obj


def _extract_next_data(html: str) -> dict[str, Any] | None:
    m = re.search(
        r'<script id="__NEXT_DATA__" type="application/json">\s*(.*?)\s*</script>',
        html,
        re.S,
    )
    if not m:
        return None
    return json.loads(m.group(1))


def main() -> None:
    url = "https://streamtoearn.io/gifts?region=UA"
    html = requests.get(url, timeout=30).text
    Path("artifacts").mkdir(exist_ok=True)
    Path("artifacts/streamtoearn_gifts_UA.html").write_text(html, encoding="utf-8")

    # The page is (usually) rendered by Next.js and may carry structured data in __NEXT_DATA__.
    next_data = _extract_next_data(html)

    # The page is server-rendered HTML with repeated "gift" cards like:
    # <div class="gift"><img src="..." alt="Rose"> ... <p class="gift-name">Rose</p>
    # <p class="gift-price">1</p>
    print(
        "marker counts:",
        html.count('class="gift"'),
        html.count("gift-name"),
        html.count("gift-price"),
    )

    parser = _GiftParser()
    parser.feed(html)
    gifts_raw = parser.gifts

    # De-dupe while preserving order (the page sometimes contains duplicates).
    seen = set()
    gifts: list[Gift] = []
    for g in gifts_raw:
        key = (g.name, g.price, g.image_url)
        if key in seen:
            continue
        seen.add(key)
        gifts.append(g)

    if next_data is not None:
        # Best-effort: collect all URLs and keep only likely image assets.
        urls = list(_iter_urls(next_data))
        img_urls = [
            u
            for u in urls
            if re.search(r"\.(png|jpg|jpeg|webp|gif)(\?|$)", u, re.I)
            or "image" in u.lower()
            or "img" in u.lower()
        ]
        # If the site has explicit gift objects with name/icon, this will be expanded later.
        # For now we just keep the list to inspect manually if needed.
        Path("artifacts").mkdir(exist_ok=True)
        Path("artifacts/streamtoearn_next_urls.json").write_text(
            json.dumps({"url": url, "img_urls": img_urls}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    out_dir = Path("artifacts")
    out_dir.mkdir(exist_ok=True)

    out_json = out_dir / "tiktok_gifts_ua_streamtoearn.json"
    out_csv = out_dir / "tiktok_gifts_ua_streamtoearn.csv"

    out_json.write_text(
        json.dumps([g.__dict__ for g in gifts], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    with out_csv.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["name", "price", "image_url"])
        w.writeheader()
        for g in gifts:
            w.writerow({"name": g.name, "price": g.price, "image_url": g.image_url or ""})

    print(f"Saved {len(gifts)} gifts to {out_json} and {out_csv}")
    if next_data is None:
        print("Note: __NEXT_DATA__ not found; images likely require a separate API or JS runtime.")
    else:
        print("Note: wrote artifacts/streamtoearn_next_urls.json with discovered image-like URLs.")


if __name__ == "__main__":
    main()
