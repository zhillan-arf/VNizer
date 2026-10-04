"""Validate avatar media and preserve selected assets for each attempt."""

import json
import shutil
import subprocess
from pathlib import Path

import pymupdf
from PIL import Image

from .files import atomic_json
from .store import MOODS, new_id

IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".webp"}
VIDEO_SUFFIXES = {".mp4", ".webm"}


def seed_avatars(store):
    with store.connect() as db:
        db.execute("BEGIN IMMEDIATE")
        for mood in MOODS:
            avatar_id = "builtin-" + mood
            if db.execute("SELECT 1 FROM avatars WHERE mood=?", (mood,)).fetchone():
                continue
            target = store.root / "avatars" / f"{avatar_id}.png"
            target.parent.mkdir(parents=True, exist_ok=True)
            svg = Path(__file__).parent / "assets" / f"{mood}.svg"
            with pymupdf.open(svg) as document:
                document[0].get_pixmap(alpha=True).save(target)
            selected = not db.execute("SELECT 1 FROM avatars WHERE mood=? AND selected=1", (mood,)).fetchone()
            db.execute("INSERT INTO avatars VALUES (?,?,?,?,?,1)",
                       (avatar_id, "VNizer guide", mood, str(target.relative_to(store.root)), int(selected)))


def validate_avatar(path):
    suffix = path.suffix.lower()
    if suffix in IMAGE_SUFFIXES:
        with Image.open(path) as image:
            if image.width * image.height > 16_000_000 or max(image.size) > 4096:
                raise ValueError("Avatar images must fit within 4096 pixels and 16 million pixels.")
            duration = 0
            for index in range(getattr(image, "n_frames", 1)):
                if index >= 900:
                    raise ValueError("The avatar contains too many animation frames.")
                image.seek(index)
                image.load()
                duration += image.info.get("duration", 100)
            if getattr(image, "n_frames", 1) > 1 and duration > 30_000:
                raise ValueError("Avatar clips must not exceed 30 seconds.")
        return
    if suffix not in VIDEO_SUFFIXES:
        raise ValueError("Use PNG, JPEG, GIF, WebP, WebM, or MP4 avatar media.")
    probe = subprocess.run(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)],
                           capture_output=True, check=True, timeout=20)
    info = json.loads(probe.stdout)
    videos = [s for s in info["streams"] if s["codec_type"] == "video"]
    if len(videos) != 1 or not 0 < float(info["format"].get("duration", 0)) <= 30:
        raise ValueError("Use a video with one video stream and a duration of at most 30 seconds.")
    video = videos[0]
    if max(video["width"], video["height"]) > 4096 or video["width"] * video["height"] > 16_000_000:
        raise ValueError("Avatar video dimensions are too large.")
    subprocess.run(["ffmpeg", "-v", "error", "-xerror", "-i", str(path), "-map", "0:v:0",
                    "-an", "-f", "null", "-"], capture_output=True, check=True, timeout=60)


def snapshot_avatars(store, document):
    seed_avatars(store)
    target = store.document_root(document) / "avatars" / str(document["attempt"])
    manifest = target / "manifest.json"
    if manifest.exists():
        return json.loads(manifest.read_text())
    target.mkdir(parents=True, exist_ok=True)
    result = {}
    with store.connect() as db:
        db.execute("BEGIN IMMEDIATE")
        for mood in MOODS:
            row = db.execute("SELECT * FROM avatars WHERE mood=? ORDER BY selected DESC,builtin DESC LIMIT 1",
                             (mood,)).fetchone()
            source = store.file_path(row["path"])
            path = target / (mood + source.suffix)
            shutil.copyfile(source, path)
            result[mood] = str(path.relative_to(store.root))
    atomic_json(manifest, result)
    return result


def add_avatar(store, path, name, mood):
    if mood not in MOODS:
        raise ValueError("Select a supported mood.")
    validate_avatar(path)
    avatar_id = new_id()
    target = store.root / "avatars" / (avatar_id + path.suffix.lower())
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(path, target)
    with store.connect() as db:
        db.execute("INSERT INTO avatars VALUES (?,?,?,?,0,0)",
                   (avatar_id, name, mood, str(target.relative_to(store.root))))
    return avatar_id
