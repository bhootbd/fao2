#!/usr/bin/env python3
"""Transcribe the speech in archived videos with faster-whisper.

Usage: python scripts/transcribe.py <media_dir> <out.json> <shard> <num_shards>
Each shard handles the videos whose index % num_shards == shard.
"""
import json
import os
import sys

from faster_whisper import WhisperModel

media, out, shard, shards = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
files = sorted(f for f in os.listdir(media) if f.endswith(".mp4"))[shard::shards]
# Optionally skip files already transcribed without error in an existing transcripts file
skip_path = os.environ.get("SKIP_JSON")
if skip_path and os.path.exists(skip_path):
    done = {k for k, v in json.load(open(skip_path, encoding="utf-8")).items() if "error" not in v}
    files = [f for f in files if f.split("__")[0].rsplit(".", 1)[0] not in done]
model = WhisperModel(os.environ.get("WHISPER_MODEL", "medium"), device="cpu", compute_type="int8")

def key(name):
    """<id>_<n> part of the file name, so transcripts survive renames."""
    return name.split("__")[0].rsplit(".", 1)[0]


results = {}
for i, name in enumerate(files):
    try:
        segments, info = model.transcribe(os.path.join(media, name), vad_filter=True, beam_size=5)
        text = " ".join(s.text.strip() for s in segments).strip()
        results[key(name)] = {"language": info.language, "language_probability": round(info.language_probability, 2), "text": text}
    except Exception as e:
        results[key(name)] = {"error": str(e)}
    r = results[key(name)]
    print(f"[{i + 1}/{len(files)}] {name}: {r.get('text', r.get('error'))[:80]}", flush=True)

with open(out, "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=1)
