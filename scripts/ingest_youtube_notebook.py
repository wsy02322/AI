#!/usr/bin/env python3
"""Ingest a YouTube URL into the YouTube Notebook knowledge collection.

Captions first; no captions → OpenRouter/OWUI Whisper ASR.
Samples frames and asks a vision model what is shown (spoken vs shown).
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stack_contract import NOTEBOOK_KNOWLEDGE_NAME

OPENWEBUI_URL = os.environ.get("OPENWEBUI_URL", "").rstrip("/")
OPENWEBUI_PASSWORD = os.environ.get("OPENWEBUI_PASSWORD")
VISION_MODEL = os.environ.get("NOTEBOOK_VISION_MODEL", "google/gemini-3.7-flash")
MAX_FRAMES = int(os.environ.get("NOTEBOOK_MAX_FRAMES", "6"))
YOUTUBE_ID_RE = re.compile(r"(?:v=|/shorts/|/embed/|youtu\.be/)([A-Za-z0-9_-]{11})")


def _login_candidates() -> list[str]:
    candidates: list[str] = []
    for value in (os.environ.get("OPENWEBUI_USERNAME"), os.environ.get("OPENWEBUI_EMAIL")):
        if value and value not in candidates:
            candidates.append(value)
    return candidates


def signin() -> str:
    if not OPENWEBUI_URL or not OPENWEBUI_PASSWORD:
        raise SystemExit("Missing OPENWEBUI_URL / OPENWEBUI_PASSWORD")
    last = ""
    for ident in _login_candidates():
        resp = requests.post(
            f"{OPENWEBUI_URL}/api/v1/auths/signin",
            json={"email": ident, "password": OPENWEBUI_PASSWORD},
            timeout=30,
        )
        if resp.status_code == 200:
            return resp.json()["token"]
        last = f"{resp.status_code} {resp.text[:160]}"
        if resp.status_code == 429:
            time.sleep(8)
    raise SystemExit(f"signin failed: {last}")


def headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def video_id(url: str) -> str:
    match = YOUTUBE_ID_RE.search(url)
    if not match:
        raise SystemExit(f"cannot parse YouTube id from {url}")
    return match.group(1)


def mmss(seconds: float) -> str:
    total = max(0, int(round(seconds)))
    return f"{total // 60:02d}:{total % 60:02d}"


def oembed(url: str) -> dict:
    try:
        resp = requests.get(
            "https://www.youtube.com/oembed",
            params={"url": url, "format": "json"},
            timeout=20,
        )
        if resp.status_code == 200:
            return resp.json()
    except Exception as exc:
        print(f"WARN oembed: {exc}")
    return {}


def owui_youtube_captions(h: dict[str, str], url: str) -> list[dict]:
    resp = requests.post(
        f"{OPENWEBUI_URL}/api/v1/retrieval/process/youtube",
        headers=h,
        json={"url": url},
        timeout=120,
    )
    if resp.status_code != 200:
        print(f"OWUI youtube loader {resp.status_code} {resp.text[:180]}")
        return []
    payload = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
    content = (
        ((payload.get("file") or {}).get("data") or {}).get("content")
        or payload.get("content")
        or ""
    )
    lines = []
    for raw in str(content).splitlines():
        text = raw.strip()
        if text:
            lines.append({"start": 0.0, "text": text, "modality": "spoken"})
    return lines


def fetch_thumbnails(vid: str, dest: Path) -> list[tuple[float, Path]]:
    names = [("0.jpg", 0.0), ("1.jpg", 5.0), ("2.jpg", 10.0), ("3.jpg", 15.0)]
    frames = []
    seen = set()
    for name, ts in names:
        url = f"https://i.ytimg.com/vi/{vid}/{name}"
        resp = requests.get(url, timeout=20)
        if resp.status_code != 200 or not resp.content or resp.headers.get("content-type", "").startswith("text"):
            continue
        digest = hash(resp.content)
        if digest in seen:
            continue
        seen.add(digest)
        path = dest / name
        path.write_bytes(resp.content)
        frames.append((ts, path))
    return frames


def fetch_captions(vid: str) -> list[dict]:
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
    except ImportError:
        print("WARN youtube_transcript_api missing")
        return []
    rows = []
    try:
        if hasattr(YouTubeTranscriptApi, "get_transcript"):
            rows = YouTubeTranscriptApi.get_transcript(
                vid, languages=["en", "zh-Hans", "zh-Hant", "zh", "ja", "ko"]
            )
        else:
            fetched = YouTubeTranscriptApi().fetch(
                vid, languages=["en", "zh", "zh-Hans", "zh-Hant", "ja", "ko"]
            )
            rows = list(fetched)
    except Exception as exc:
        print(f"captions fetch failed: {exc}")
        return []
    out = []
    for row in rows:
        if hasattr(row, "text"):
            start = float(getattr(row, "start", 0) or 0)
            text = (getattr(row, "text", "") or "").replace("\n", " ").strip()
        else:
            start = float(row.get("start") or 0)
            text = (row.get("text") or "").replace("\n", " ").strip()
        if text:
            out.append({"start": start, "text": text, "modality": "spoken"})
    return out


def openrouter_from_audio(h: dict[str, str]) -> tuple[str, str]:
    audio = requests.get(f"{OPENWEBUI_URL}/api/v1/audio/config", headers=h, timeout=30).json()
    tts = audio.get("tts") or {}
    return tts.get("OPENAI_API_BASE_URL", "").rstrip("/"), tts.get("OPENAI_API_KEY") or ""


def asr_whisper(h: dict[str, str], wav_path: Path) -> list[dict]:
    with wav_path.open("rb") as handle:
        resp = requests.post(
            f"{OPENWEBUI_URL}/api/v1/audio/transcriptions",
            headers={"Authorization": h["Authorization"]},
            files={"file": (wav_path.name, handle, "audio/wav")},
            timeout=180,
        )
    if resp.status_code != 200:
        raise RuntimeError(f"STT {resp.status_code} {resp.text[:300]}")
    payload = resp.json()
    text = (payload.get("text") or "").strip()
    if not text:
        return []
    return [{"start": 0.0, "text": text, "modality": "spoken"}]


def run(cmd: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=cwd, check=False, capture_output=True, text=True)


def download_media(url: str, dest: Path, audio_only: bool) -> Path | None:
    yt = shutil.which("yt-dlp")
    if not yt:
        print("WARN yt-dlp not installed")
        return None
    out = dest / ("audio.%(ext)s" if audio_only else "video.%(ext)s")
    args = [yt, "--no-playlist", "-o", str(out), url]
    if audio_only:
        args[1:1] = ["-x", "--audio-format", "wav"]
    else:
        args[1:1] = ["-f", "mp4/best[height<=480]/best", "--max-filesize", "40M"]
    proc = run(args)
    if proc.returncode != 0:
        print(f"WARN yt-dlp failed: {proc.stderr[-400:]}")
        return None
    files = list(dest.glob("audio.*")) if audio_only else list(dest.glob("video.*"))
    return files[0] if files else None


def sample_frames(video: Path, dest: Path, count: int) -> list[tuple[float, Path]]:
    probe = run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(video),
        ]
    )
    try:
        duration = float((probe.stdout or "0").strip() or "0")
    except ValueError:
        duration = 0
    if duration <= 0:
        duration = 19.0
    times = [duration * (i + 1) / (count + 1) for i in range(count)]
    frames = []
    for idx, ts in enumerate(times):
        png = dest / f"frame_{idx:02d}.jpg"
        proc = run(
            [
                "ffmpeg",
                "-y",
                "-ss",
                f"{ts:.2f}",
                "-i",
                str(video),
                "-frames:v",
                "1",
                "-vf",
                "scale=640:-1",
                str(png),
            ]
        )
        if proc.returncode == 0 and png.exists() and png.stat().st_size > 0:
            frames.append((ts, png))
    return frames


def describe_frame(or_base: str, or_key: str, ts: float, png: Path) -> str:
    b64 = base64.b64encode(png.read_bytes()).decode("ascii")
    resp = requests.post(
        f"{or_base}/chat/completions",
        headers={"Authorization": f"Bearer {or_key}", "Content-Type": "application/json"},
        json={
            "model": VISION_MODEL,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": (
                                f"This is a YouTube frame at {mmss(ts)}. "
                                "Describe on-screen text, slides, diagrams, or visible objects. "
                                "One or two sentences. If nothing readable, say so."
                            ),
                        },
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{b64}"},
                        },
                    ],
                }
            ],
            "max_tokens": 200,
        },
        timeout=90,
    )
    if resp.status_code != 200:
        return f"(vision failed {resp.status_code})"
    data = resp.json()
    return (
        (((data.get("choices") or [{}])[0].get("message") or {}).get("content") or "")
        .strip()
        or "(empty vision)"
    )


def find_knowledge(h: dict[str, str]) -> str:
    listed = requests.get(f"{OPENWEBUI_URL}/api/v1/knowledge/", headers=h, timeout=30).json()
    items = listed.get("items") if isinstance(listed, dict) else listed
    for item in items or []:
        if item.get("name") == NOTEBOOK_KNOWLEDGE_NAME:
            return item["id"]
    raise SystemExit(f"knowledge {NOTEBOOK_KNOWLEDGE_NAME!r} missing; run apply_notebook_n1.py")


def upload_and_attach(token: str, kid: str, path: Path) -> str:
    auth = {"Authorization": f"Bearer {token}"}
    with path.open("rb") as handle:
        uploaded = requests.post(
            f"{OPENWEBUI_URL}/api/v1/files/",
            headers=auth,
            files={"file": (path.name, handle, "text/markdown")},
            timeout=60,
        )
    if uploaded.status_code != 200:
        raise RuntimeError(f"file upload {uploaded.status_code} {uploaded.text[:300]}")
    file_id = uploaded.json()["id"]
    added = requests.post(
        f"{OPENWEBUI_URL}/api/v1/knowledge/{kid}/file/add",
        headers=headers(token),
        json={"file_id": file_id},
        timeout=120,
    )
    if added.status_code != 200:
        raise RuntimeError(f"knowledge add {added.status_code} {added.text[:400]}")
    return file_id


def build_markdown(url: str, vid: str, spoken: list[dict], shown: list[dict], source: str) -> str:
    lines = [
        f"# YouTube source {vid}",
        "",
        f"- url: {url}",
        f"- watch: https://youtu.be/{vid}",
        f"- spoken_source: {source}",
        "",
        "## Spoken",
        "",
    ]
    if spoken:
        for row in spoken:
            lines.append(
                f"- [{mmss(row['start'])}] spoken: {row['text']} "
                f"(https://youtu.be/{vid}?t={int(row['start'])})"
            )
    else:
        lines.append("- (no spoken transcript)")
    lines.extend(["", "## Shown", ""])
    if shown:
        for row in shown:
            lines.append(
                f"- [{mmss(row['start'])}] shown: {row['text']} "
                f"(https://youtu.be/{vid}?t={int(row['start'])})"
            )
    else:
        lines.append("- (no visual timeline)")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True)
    parser.add_argument("--force-asr", action="store_true")
    args = parser.parse_args()
    url = args.url.strip()
    vid = video_id(url)
    token = signin()
    h = headers(token)
    or_base, or_key = openrouter_from_audio(h)

    spoken: list[dict] = []
    source = "none"
    if not args.force_asr:
        spoken = owui_youtube_captions(h, url)
        if spoken:
            source = "owui-youtube-loader"
        else:
            spoken = fetch_captions(vid)
            if spoken:
                source = "captions"
    meta = oembed(url)
    title = meta.get("title") or vid
    with tempfile.TemporaryDirectory(prefix="ytnb-") as raw:
        tmp = Path(raw)
        if not spoken:
            audio = download_media(url, tmp, audio_only=True)
            if audio:
                spoken = asr_whisper(h, audio)
                source = "asr" if spoken else "asr-empty"
        shown: list[dict] = []
        video = download_media(url, tmp, audio_only=False)
        frames: list[tuple[float, Path]] = []
        if video and or_base and or_key:
            frames = sample_frames(video, tmp, MAX_FRAMES)
        if not frames:
            frames = fetch_thumbnails(vid, tmp)
            print(f"using YouTube storyboard thumbs: {len(frames)}")
        if or_base and or_key:
            for ts, png in frames:
                shown.append(
                    {
                        "start": ts,
                        "text": describe_frame(or_base, or_key, ts, png),
                        "modality": "shown",
                    }
                )
        header_url = url
        markdown = build_markdown(header_url, vid, spoken, shown, source)
        if title:
            markdown = f"Title: {title}\n\n" + markdown
        md_path = tmp / f"youtube-{vid}.md"
        md_path.write_text(markdown, encoding="utf-8")
        kid = find_knowledge(h)
        file_id = upload_and_attach(token, kid, md_path)
        print(json.dumps({
            "video_id": vid,
            "title": title,
            "spoken_source": source,
            "spoken": len(spoken),
            "shown": len(shown),
            "knowledge_id": kid,
            "file_id": file_id,
        }))
        if not shown:
            raise SystemExit("ingest produced no visual timeline")
        if not spoken:
            print("WARN no spoken transcript (YouTube bot-check on this IP); visual timeline still stored")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
