#!/usr/bin/env python3
"""Crawl recent foreign news articles and save them as Markdown corpus.

Default sources:
    - NPR Education (RSS id=1013)
    - The Guardian Society section

Output:
    <out_dir>/原始语料_<theme>/
        <pub_date>_<source>_<slug>.md
    <briefing_path> (HTML summary with collapsible panels)
"""
import argparse
import html
import os
import re
import time
from datetime import datetime
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


def make_session():
    s = requests.Session()
    s.headers.update(HEADERS)
    retries = Retry(total=3, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
    s.mount("https://", HTTPAdapter(max_retries=retries))
    return s


SESSION = make_session()


def slugify(text: str) -> str:
    s = re.sub(r"[^\w\s-]", "", text).strip().lower()
    s = re.sub(r"[-\s]+", "-", s)
    return s[:60].strip("-")


def url_slug(url: str) -> str:
    path = urlparse(url).path.rstrip("/")
    last = path.split("/")[-1]
    return slugify(last.replace("-", " "))


def parse_date_from_pubdate(pub: str) -> str:
    m = re.search(r"(\d{1,2})\s+(\w+)\s+(\d{4})", pub)
    if m:
        try:
            dt = datetime.strptime(f"{m.group(1)} {m.group(2)} {m.group(3)}", "%d %b %Y")
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            pass
    return ""


def clean_npr_text(text: str) -> str:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    drop = {
        "hide caption",
        "toggle caption",
        "sponsor message",
        "listen",
        "transcript",
        "toggle more options",
    }
    cleaned = []
    for line in lines:
        low = line.lower()
        if low in drop:
            continue
        if low.endswith(" for npr") or low.endswith(" for the new york times"):
            continue
        if low.startswith("image credit:") or low.startswith("(image credit:"):
            continue
        cleaned.append(line)
    return "\n\n".join(cleaned)


def clean_guardian_text(text: str) -> str:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    cleaned = []
    for line in lines:
        low = line.lower()
        if low.startswith("photograph:") or low.startswith("image credit:"):
            continue
        cleaned.append(line)
    return "\n\n".join(cleaned)


class CorpusSaver:
    def __init__(self, out_dir: str, theme: str, min_word_count: int = 200):
        self.corpus_dir = os.path.join(out_dir, f"原始语料_{theme}")
        self.min_word_count = min_word_count
        os.makedirs(self.corpus_dir, exist_ok=True)
        self.saved = []

    def save(self, title: str, source: str, url: str, pub_date: str, body: str):
        wc = len(body.split())
        if wc < self.min_word_count:
            print(f"  SKIP (too short: {wc} words): {title}")
            return
        title_slug = slugify(title) or url_slug(url)
        filename = f"{pub_date}_{source.replace(' ', '-')}_{title_slug}.md"
        path = os.path.join(self.corpus_dir, filename)
        content = (
            f"---\n"
            f"title: {title}\n"
            f"source: {source}\n"
            f"url: {url}\n"
            f"pub_date: {pub_date}\n"
            f"word_count: {wc}\n"
            f"downloaded: {datetime.now().isoformat()}\n"
            f"---\n\n"
            f"# {title}\n\n"
            f"**Source:** {source}\n\n"
            f"**URL:** {url}\n\n"
            f"**Published:** {pub_date}\n\n"
            f"{body}\n"
        )
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"  SAVED ({wc} words): {path}")
        self.saved.append({
            "path": path,
            "title": title,
            "source": source,
            "url": url,
            "pub_date": pub_date,
            "word_count": wc,
            "body": body,
        })


def fetch_npr(saver: CorpusSaver, max_articles: int):
    rss_url = "https://www.npr.org/rss/rss.php?id=1013"
    print(f"Fetching NPR Education RSS: {rss_url}")
    try:
        r = SESSION.get(rss_url, timeout=30)
        r.raise_for_status()
    except Exception as e:
        print(f"   -> error fetching NPR RSS: {e}")
        return

    soup = BeautifulSoup(r.content, "xml")
    items = soup.find_all("item")[:max_articles + 5]
    seen_urls = set()
    count = 0
    for item in items:
        if count >= max_articles:
            break
        title = item.title.get_text(strip=True) if item.title else "untitled"
        link = item.link.get_text(strip=True) if item.link else ""
        pub = item.pubDate.get_text(strip=True) if item.pubDate else ""
        pub_short = parse_date_from_pubdate(pub)
        if not link or not pub_short or link in seen_urls:
            continue
        seen_urls.add(link)
        if link.endswith("-e1") or "/podcasts/" in link:
            continue
        print(f" NPR: {title[:80]}")
        try:
            ar = SESSION.get(link, timeout=30)
            ar.raise_for_status()
            asoup = BeautifulSoup(ar.text, "lxml")
            story = asoup.select_one("div.storytext")
            if not story:
                print("   -> no storytext div")
                continue
            body = clean_npr_text(story.get_text("\n\n", strip=True))
            saver.save(title, "NPR Education", link, pub_short, body)
            count += 1
            time.sleep(1.5)
        except Exception as e:
            print(f"   -> error: {e}")


def fetch_guardian(saver: CorpusSaver, max_articles: int, year: int = None):
    year = year or datetime.now().year
    section_url = "https://www.theguardian.com/society"
    print(f"Fetching Guardian Society section: {section_url}")
    try:
        r = SESSION.get(section_url, timeout=30)
        r.raise_for_status()
    except Exception as e:
        print(f"   -> error fetching Guardian section: {e}")
        return

    soup = BeautifulSoup(r.text, "lxml")
    seen = set()
    article_links = []
    pattern = re.compile(rf"^https://www\.theguardian\.com/society/{year}/")
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if href.startswith("/"):
            href = f"https://www.theguardian.com{href}"
        if not pattern.match(href):
            continue
        if href in seen:
            continue
        seen.add(href)
        article_links.append(href)
        if len(article_links) >= max_articles + 5:
            break

    count = 0
    for link in article_links:
        if count >= max_articles:
            break
        print(f" Guardian: {link[:100]}")
        try:
            ar = SESSION.get(link, timeout=30)
            ar.raise_for_status()
            asoup = BeautifulSoup(ar.text, "lxml")
            h1 = asoup.find("h1")
            title = h1.get_text(strip=True) if h1 else url_slug(link).replace("-", " ").title()
            body_el = asoup.select_one(".article-body-commercial-selector")
            if not body_el:
                print("   -> no article body selector")
                continue

            date_el = asoup.select_one("time")
            pub_short = ""
            if date_el and date_el.get("datetime"):
                try:
                    pub_short = datetime.fromisoformat(date_el["datetime"].replace("Z", "+00:00")).strftime("%Y-%m-%d")
                except ValueError:
                    pass
            if not pub_short:
                m = re.search(r"/society/(\d{4})/(\w+)/(\d{1,2})/", link)
                if m:
                    try:
                        pub_short = datetime.strptime(f"{m.group(1)} {m.group(2)} {m.group(3)}", "%Y %b %d").strftime("%Y-%m-%d")
                    except ValueError:
                        pub_short = m.group(1)
                else:
                    pub_short = f"{year}-01-01"

            body = clean_guardian_text(body_el.get_text("\n\n", strip=True))
            saver.save(title, "The Guardian Society", link, pub_short, body)
            count += 1
            time.sleep(1.5)
        except Exception as e:
            print(f"   -> error: {e}")


def generate_briefing(articles, out_path: str):
    if not articles:
        print("No articles saved; skipping briefing.")
        return
    articles.sort(key=lambda x: x["pub_date"], reverse=True)
    total_words = sum(a["word_count"] for a in articles)
    sources = sorted(set(a["source"] for a in articles))
    dates = sorted([a["pub_date"] for a in articles])

    parts = []
    parts.append("<!DOCTYPE html>")
    parts.append('<html lang="zh-CN">')
    parts.append("<head>")
    parts.append('  <meta charset="UTF-8">')
    parts.append("  <title>语料采集简报</title>")
    parts.append("  <style>")
    parts.append("    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Microsoft YaHei', sans-serif; max-width: 900px; margin: 2rem auto; padding: 0 1rem; line-height: 1.6; color: #222; }")
    parts.append("    h1 { font-size: 1.6rem; margin-bottom: 0.5rem; }")
    parts.append("    .stats { background: #f5f5f5; padding: 1rem; border-radius: 6px; margin-bottom: 1.5rem; }")
    parts.append("    .stats p { margin: 0.25rem 0; }")
    parts.append("    details { border: 1px solid #ddd; border-radius: 6px; margin-bottom: 1rem; padding: 0.75rem; }")
    parts.append("    summary { cursor: pointer; font-weight: 600; }")
    parts.append("    .meta { color: #666; font-size: 0.9rem; margin: 0.25rem 0 0.5rem; }")
    parts.append("    .excerpt { color: #333; white-space: pre-wrap; }")
    parts.append("    a { color: #0066cc; }")
    parts.append("  </style>")
    parts.append("</head>")
    parts.append("<body>")
    parts.append("  <h1>语料采集简报</h1>")
    parts.append('  <div class="stats">')
    parts.append(f"    <p><strong>文章总数：</strong>{len(articles)} 篇</p>")
    parts.append(f"    <p><strong>来源：</strong>{', '.join(sources)}</p>")
    parts.append(f"    <p><strong>总字数：</strong>{total_words:,} 词</p>")
    parts.append(f"    <p><strong>日期范围：</strong>{dates[0]} 至 {dates[-1]}</p>")
    parts.append("  </div>")

    for a in articles:
        excerpt = " ".join(a["body"].split()[:80])
        parts.append("  <details>")
        parts.append(f"    <summary>{html.escape(a['title'])}</summary>")
        parts.append('    <p class="meta">')
        parts.append(f"      来源：{html.escape(a['source'])} &nbsp;|&nbsp; 发布日期：{a['pub_date']} &nbsp;|&nbsp; 字数：{a['word_count']} &nbsp;|&nbsp; <a href=\"{html.escape(a['url'])}\" target=\"_blank\">原文链接</a>")
        parts.append("    </p>")
        parts.append(f"    <p class='excerpt'>{html.escape(excerpt)}...</p>")
        parts.append("  </details>")

    parts.append("</body>")
    parts.append("</html>")

    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(parts))
    print(f"BRIEFING: {out_path}")


def main():
    parser = argparse.ArgumentParser(description="Crawl foreign news articles for test creation.")
    parser.add_argument("--out-dir", default=".", help="Output directory")
    parser.add_argument("--theme", default="人与社会", help="Theme label for corpus folder")
    parser.add_argument("--sources", default="npr,guardian", help="Comma-separated source names")
    parser.add_argument("--max-per-source", type=int, default=10, help="Max articles per source")
    parser.add_argument("--min-word-count", type=int, default=200, help="Minimum article word count")
    parser.add_argument("--briefing", default="", help="Path to write HTML briefing")
    parser.add_argument("--year", type=int, default=0, help="Year filter for Guardian URLs")
    args = parser.parse_args()

    try:
        import requests  # noqa: F401
        import bs4  # noqa: F401
    except ImportError as e:
        print("Missing dependency. Install with: pip install --user requests beautifulsoup4 lxml python-docx")
        raise SystemExit(1) from e

    saver = CorpusSaver(args.out_dir, args.theme, args.min_word_count)
    sources = [s.strip().lower() for s in args.sources.split(",")]

    if "npr" in sources:
        fetch_npr(saver, args.max_per_source)
    if "guardian" in sources:
        fetch_guardian(saver, args.max_per_source, year=args.year or None)

    briefing_path = args.briefing or os.path.join(args.out_dir, "语料采集简报.html")
    generate_briefing(saver.saved, briefing_path)


if __name__ == "__main__":
    main()
