#!/usr/bin/env python3
"""Archive a public Telegram channel using its web preview (t.me/s/<channel>).

No login needed. Downloads photos and videos the preview exposes and writes
an index.json with each post's text and media. Re-runs skip files already saved.

Usage: python scripts/tg_scrape.py <channel> [out_dir]
"""
import html
import json
import os
import re
import subprocess
import sys
import time
import urllib.request

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"
MAX_BYTES = 95 * 1024 * 1024  # GitHub rejects files over 100 MB
# Every CHECKPOINT_EVERY new files, save index.json and run $CHECKPOINT_CMD (e.g. git commit + push)
CHECKPOINT_EVERY = int(os.environ.get("CHECKPOINT_EVERY", "200"))

POST_RE = re.compile(r'<div class="tgme_widget_message_wrap.*?(?=<div class="tgme_widget_message_wrap|\Z)', re.S)
ID_RE = re.compile(r'data-post="[^/"]+/(\d+)"')
PHOTO_RE = re.compile(r"tgme_widget_message_photo_wrap[^>]*background-image:url\('([^']+)'\)")
VIDEO_RE = re.compile(r'<video[^>]+src="([^"]+)"')
TEXT_RE = re.compile(r'<div class="tgme_widget_message_text[^"]*"[^>]*>(.*?)</div>', re.S)
DATE_RE = re.compile(r'<time datetime="([^"]+)"')
DOC_RE = re.compile(r'tgme_widget_message_document_title[^>]*>(.*?)</div>', re.S)


def get(url, retries=4):
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read()
        except Exception as e:
            if i == retries - 1:
                raise
            print(f"  retry {url}: {e}", file=sys.stderr)
            time.sleep(2 ** (i + 1))


def strip_tags(s):
    s = re.sub(r"<br\s*/?>", "\n", s)
    return html.unescape(re.sub(r"<[^>]+>", "", s)).strip()


def ext_of(url, default):
    m = re.search(r"\.(\w{2,4})(?:\?|$)", url)
    return "." + m.group(1) if m else default


def main():
    channel = sys.argv[1].lstrip("@")
    out = sys.argv[2] if len(sys.argv) > 2 else os.path.join("archive", channel)
    media_dir = os.path.join(out, "media")
    os.makedirs(media_dir, exist_ok=True)
    index_path = os.path.join(out, "index.json")
    index = {}
    if os.path.exists(index_path):
        index = {p["id"]: p for p in json.load(open(index_path, encoding="utf-8"))}

    def save_index():
        with open(index_path, "w", encoding="utf-8") as f:
            json.dump(sorted(index.values(), key=lambda p: p["id"]), f, ensure_ascii=False, indent=1)

    def checkpoint():
        save_index()
        cmd = os.environ.get("CHECKPOINT_CMD")
        if cmd:
            print(f"checkpoint: {len(index)} posts", flush=True)
            subprocess.run(cmd, shell=True, check=False)

    new_files = 0
    renamed = {}
    catalog_path = os.path.join(out, "catalog.json")
    if os.path.exists(catalog_path):
        renamed = {c["key"]: os.path.basename(c["file"]) for c in json.load(open(catalog_path, encoding="utf-8"))}

    before = None
    while True:
        url = f"https://t.me/s/{channel}" + (f"?before={before}" if before else "")
        page = get(url).decode("utf-8", "replace")
        posts = POST_RE.findall(page)
        ids = []
        for block in posts:
            m = ID_RE.search(block)
            if not m:
                continue
            pid = int(m.group(1))
            ids.append(pid)
            text = TEXT_RE.search(block)
            date = DATE_RE.search(block)
            entry = {
                "id": pid,
                "link": f"https://t.me/{channel}/{pid}",
                "date": date.group(1) if date else None,
                "text": strip_tags(text.group(1)) if text else "",
                "media": [],
                "documents_not_downloadable": [strip_tags(d) for d in DOC_RE.findall(block)],
            }
            urls = [(u, ".jpg") for u in PHOTO_RE.findall(block)] + [(u, ".mp4") for u in VIDEO_RE.findall(block)]
            for n, (murl, default_ext) in enumerate(urls):
                name = f"{pid:06d}_{n}{ext_of(murl, default_ext)}"
                # Files may have been renamed (see catalog.json); reuse that name
                if renamed.get(f"{pid:06d}_{n}"):
                    name = renamed[f"{pid:06d}_{n}"]
                path = os.path.join(media_dir, name)
                if not os.path.exists(path):
                    try:
                        data = get(html.unescape(murl))
                    except Exception as e:
                        print(f"  failed {pid}/{n}: {e}", file=sys.stderr)
                        continue
                    if len(data) > MAX_BYTES:
                        print(f"  skipped {name}: too large ({len(data)} bytes)")
                        continue
                    with open(path, "wb") as f:
                        f.write(data)
                    new_files += 1
                    if new_files % CHECKPOINT_EVERY == 0:
                        checkpoint()
                entry["media"].append(f"media/{name}")
            index[pid] = entry
        if not ids:
            break
        oldest = min(ids)
        print(f"page before={before}: {len(ids)} posts, oldest #{oldest}, total {len(index)}", flush=True)
        if before is not None and oldest >= before:
            break
        before = oldest
        if oldest <= 1:
            break
        time.sleep(1)

    save_index()
    print(f"done: {len(index)} posts in {out}")


if __name__ == "__main__":
    main()
