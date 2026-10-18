#!/usr/bin/env python3
"""Delete duplicate media files found by a duplicate scan and drop them from the catalog.

Usage: python scripts/remove_duplicates.py <archive_dir> <groups.json>
groups.json: {"groups": [[file, file, ...], ...]} (file names inside <archive_dir>/media).
In each group the file with the smallest catalog key (or name) is kept. Removed files are listed in
<archive_dir>/removed.json so later downloads skip them.
"""
import json
import os
import subprocess
import sys

archive, groups_path = sys.argv[1], sys.argv[2]
media = os.path.join(archive, "media")
catalog_path = os.path.join(archive, "catalog.json")
index_path = os.path.join(archive, "index.json")
removed_path = os.path.join(archive, "removed.json")

catalog = json.load(open(catalog_path, encoding="utf-8"))
by_file = {os.path.basename(e["file"]): e for e in catalog}
removed = json.load(open(removed_path, encoding="utf-8")) if os.path.exists(removed_path) else []

def order(f):
    e = by_file.get(f, {})
    return (e.get("key") or f, f)

drop = {}
for group in json.load(open(groups_path))["groups"]:
    group = [f for f in group if os.path.exists(os.path.join(media, f))]
    if len(group) < 2:
        continue
    keep, *dups = sorted(group, key=order)
    for f in dups:
        drop[f] = keep

for f, keep in drop.items():
    subprocess.run(["git", "rm", "-q", os.path.join(media, f)], check=True)
    e = by_file.get(f, {})
    removed.append({"file": f, "key": e.get("key"), "duplicate_of": keep})

catalog = [e for e in catalog if os.path.basename(e["file"]) not in drop]
with open(catalog_path, "w", encoding="utf-8") as fh:
    json.dump(catalog, fh, ensure_ascii=False, indent=1)
if os.path.exists(index_path):
    index = json.load(open(index_path, encoding="utf-8"))
    for p in index:
        p["media"] = [m for m in p["media"] if os.path.basename(m) not in drop]
    with open(index_path, "w", encoding="utf-8") as fh:
        json.dump(index, fh, ensure_ascii=False, indent=1)
with open(removed_path, "w", encoding="utf-8") as fh:
    json.dump(removed, fh, ensure_ascii=False, indent=1)
print(f"removed {len(drop)} duplicates, catalog now {len(catalog)} entries")
