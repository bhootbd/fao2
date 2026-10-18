#!/usr/bin/env python3
"""Merge catalog entries into catalog.json and rename media files to descriptive names.

Usage: python scripts/apply_catalog.py <archive_dir> <entries.json>
Each entry has "key" (<post id>_<n>) and "slug"; the file becomes <slug>.<ext> (with -2, -3 ...
added if the name is taken). catalog.json maps each key to its file, and index.json media paths
are updated to match.
"""
import json
import os
import subprocess
import sys

archive, entries_path = sys.argv[1], sys.argv[2]
media = os.path.join(archive, "media")
catalog_path = os.path.join(archive, "catalog.json")
index_path = os.path.join(archive, "index.json")

catalog = {e["key"]: e for e in json.load(open(catalog_path, encoding="utf-8"))} if os.path.exists(catalog_path) else {}
index = json.load(open(index_path, encoding="utf-8"))
captions = {p["id"]: p["text"] for p in index}
current = {}  # key -> current file name in media/
for f in os.listdir(media):
    k = f.split("__")[0].rsplit(".", 1)[0]
    if k[:6].isdigit() and "_" in k:
        current[k] = f
for c in catalog.values():
    if os.path.exists(os.path.join(archive, c["file"])):
        current[c["key"]] = os.path.basename(c["file"])
taken = set(os.listdir(media))
renames = {}

for e in json.load(open(entries_path, encoding="utf-8")):
    key = e.pop("key", None) or e.pop("file").split("__")[0].rsplit(".", 1)[0]
    e.pop("file", None)
    old = current.get(key)
    if not old:
        print("missing file for", key)
        continue
    ext = old.rsplit(".", 1)[1]
    new, n = f"{e['slug']}.{ext}", 2
    while new != old and new in taken:
        new, n = f"{e['slug']}-{n}.{ext}", n + 1
    if old != new:
        subprocess.run(["git", "mv", os.path.join(media, old), os.path.join(media, new)], check=True)
        taken.discard(old)
        taken.add(new)
        renames[f"media/{old}"] = f"media/{new}"
    post = int(key.split("_")[0])
    catalog[key] = {"key": key, "file": f"media/{new}", "post": post,
                    "link": f"https://t.me/{os.path.basename(os.path.normpath(archive))}/{post}", "caption": captions.get(post, ""), **e}

for p in index:
    p["media"] = [renames.get(m, m) for m in p["media"]]

with open(index_path, "w", encoding="utf-8") as f:
    json.dump(index, f, ensure_ascii=False, indent=1)
with open(catalog_path, "w", encoding="utf-8") as f:
    json.dump(sorted(catalog.values(), key=lambda c: c["key"]), f, ensure_ascii=False, indent=1)
print(f"renamed {len(renames)}, catalog has {len(catalog)} entries")
