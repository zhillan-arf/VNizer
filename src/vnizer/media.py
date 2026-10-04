"""Create audio-only and visual novel MP4 outputs from narration chunks."""

import json
import os
import subprocess
import sys
import time
import wave
from pathlib import Path

import httpx
from PIL import Image, ImageDraw, ImageFont

from .avatars import snapshot_avatars
from .files import atomic_bytes, atomic_json, digest_file, digest_json
from .services import headers
from .tts import pcm_to_wav, service_type, speech_request

FONT = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
if not Path(FONT).exists():
    FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"


def run_ffmpeg(arguments):
    result = subprocess.run([sys.executable, "-m", "vnizer.child", str(os.getpid()), "ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *arguments],
                            capture_output=True, timeout=3600, check=False)
    if result.returncode:
        raise ValueError("Media encoding failed: " + result.stderr.decode(errors="replace")[-1200:])


def wav_info(path):
    with wave.open(str(path), "rb") as audio:
        duration = audio.getnframes() / audio.getframerate()
        if audio.getnchannels() not in (1, 2) or audio.getsampwidth() != 2 or not 0 < duration <= 180:
            raise ValueError("TTS must return a valid PCM16 WAV of at most 180 seconds.")
        expected = audio.getnframes() * audio.getnchannels() * audio.getsampwidth()
        if len(audio.readframes(audio.getnframes())) != expected:
            raise ValueError("The TTS WAV is truncated.")
        return duration


def speech_chunk(client, settings, chunk, path):
    url, payload = speech_request(settings, chunk)
    for attempt in range(3):
        try:
            with client.stream("POST", url,
                               headers=headers(settings.get("tts_api_key")), json=payload) as response:
                response.raise_for_status()
                data = bytearray()
                for block in response.iter_bytes():
                    data.extend(block)
                    if len(data) > 40 * 1024 * 1024:
                        raise ValueError("The TTS response exceeds the audio size limit.")
            if service_type(settings) == "supertonic":
                content_type = response.headers.get("content-type", "").split(";")[0]
                if content_type != "application/octet-stream":
                    raise ValueError("Supertonic must return raw PCM audio.")
                data = pcm_to_wav(data, response.headers.get("x-sample-rate", "24000"))
            temporary = path.with_suffix(".part.wav")
            atomic_bytes(temporary, data)
            duration = wav_info(temporary)
            temporary.replace(path)
            return duration
        except (httpx.TimeoutException, httpx.NetworkError, httpx.HTTPStatusError) as exc:
            retryable = not isinstance(exc, httpx.HTTPStatusError) or exc.response.status_code >= 500 or exc.response.status_code == 429
            if not retryable or attempt == 2:
                raise ValueError("TTS request failed. Check the service and retry the media stage.") from exc
            time.sleep(2 ** attempt)
    raise RuntimeError("The TTS request did not finish.")


def font(size):
    return ImageFont.truetype(os.getenv("VNIZER_FONT", FONT), size)


def wrap_text(text, face, width):
    lines = []
    current = ""
    for word in text.split():
        proposed = (current + " " + word).strip()
        if face.getlength(proposed) <= width:
            current = proposed
            continue
        if current:
            lines.append(current)
        current = ""
        for char in word:
            if current and face.getlength(current + char) > width:
                lines.append(current)
                current = ""
            current += char
    if current:
        lines.append(current)
    return lines


def panels(text):
    lines = wrap_text(text, font(28), 640)
    return [lines[i:i + 12] for i in range(0, len(lines), 12)]


def scene(path, document, chunk, lines):
    image = Image.new("RGB", (1280, 720), "#eaf0eb")
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, 1280, 12), fill="#327c86")
    draw.rounded_rectangle((24, 76, 486, 686), radius=24, fill="#d7e4df")
    draw.rounded_rectangle((512, 76, 1256, 686), radius=24, fill="#fcfaf4")
    title_lines = wrap_text(document["name"], font(22), 1130)
    title = title_lines[0] + (" …" if len(title_lines) > 1 else "")
    draw.text((34, 30), title, font=font(22), fill="#203841")
    draw.text((548, 104), "DOCUMENT NARRATION", font=font(16), fill="#327c86")
    for index, line in enumerate(lines):
        draw.text((548, 160 + 37 * index), line, font=font(28), fill="#203841")
    draw.line((548, 630, 1220, 630), fill="#d0dcd7", width=2)
    draw.text((548, 647), f"Page {chunk['page']}  ·  {chunk['mood'].capitalize()}",
              font=font(18), fill="#526b72")
    image.save(path)


def avatar_input(path, directory):
    # Decode animated images to a video because FFmpeg support differs by format.
    if path.suffix.lower() in (".gif", ".webp"):
        with Image.open(path) as image:
            if getattr(image, "n_frames", 1) > 1:
                frames = []
                for i in range(image.n_frames):
                    image.seek(i)
                    frame = directory / f"avatar-{i:04}.png"
                    image.convert("RGBA").save(frame)
                    duration = max(0.02, image.info.get("duration", 100) / 1000)
                    frames.append((frame, duration))
                listing = directory / "avatar-frames.txt"
                listing.write_text("".join(f"file '{p.name}'\nduration {d}\n" for p, d in frames)
                                   + f"file '{frames[-1][0].name}'\n")
                output = directory / "avatar.mov"
                run_ffmpeg(["-f", "concat", "-safe", "0", "-i", str(listing), "-an",
                            "-c:v", "qtrle", "-pix_fmt", "argb", str(output)])
                return ["-stream_loop", "-1", "-i", str(output)]
            still = directory / "avatar.png"
            image.convert("RGBA").save(still)
            return ["-loop", "1", "-i", str(still)]
    if path.suffix.lower() in (".mp4", ".webm", ".mov"):
        return ["-stream_loop", "-1", "-i", str(path)]
    return ["-loop", "1", "-i", str(path)]


def render_document(store, document, client=None):
    root = store.document_root(document)
    content = json.loads((root / "chunks.json").read_text())
    chunks = content["chunks"]
    if not chunks:
        raise ValueError("No narration chunks are available.")
    store.update_document(document["id"], state="rendering", stage="media", progress=0, total=2 * len(chunks))
    settings = json.loads(document["settings"])
    avatars = snapshot_avatars(store, document)
    work = root / "render"
    work.mkdir(exist_ok=True)
    speech = root / "speech"
    speech.mkdir(exist_ok=True)
    owned_client = client is None
    client = client or httpx.Client(timeout=httpx.Timeout(300, connect=10), follow_redirects=False)
    paths = []
    durations = []
    try:
        for index, chunk in enumerate(chunks):
            if store.is_canceled(document["id"]):
                raise InterruptedError("Process canceled.")
            path = speech / f"{index:06}.wav"
            metadata_path = path.with_suffix(".json")
            identity = digest_json({"text": chunk["text"], "mood": chunk["mood"],
                                    "speaker": settings["speaker"], "language": settings["language"],
                                    **({"tts_type": "supertonic"} if service_type(settings) == "supertonic" else {})})
            cached = json.loads(metadata_path.read_text()) if metadata_path.exists() else {}
            if path.exists() and cached.get("identity") == identity and cached.get("sha256") == digest_file(path):
                duration = wav_info(path)
            else:
                duration = speech_chunk(client, settings, chunk, path)
                atomic_json(metadata_path, {"identity": identity, "sha256": digest_file(path)})
            # Normalize every chunk before concatenation to prevent sample-rate changes.
            normalized = work / f"speech-{index:06}.wav"
            run_ffmpeg(["-i", str(path), "-ar", "24000", "-ac", "1", "-c:a", "pcm_s16le", str(normalized)])
            paths.append(normalized)
            durations.append(duration)
            store.add_artifact(document["id"], "speech", path)
            store.update_document(document["id"], progress=index + 1, total=2 * len(chunks))
    finally:
        if owned_client:
            client.close()
    audio_list = work / "speech.txt"
    audio_list.write_text("".join(f"file '{p.name}'\n" for p in paths))
    audio = root / "audio.part.mp4"
    run_ffmpeg(["-f", "concat", "-safe", "0", "-i", str(audio_list), "-vn", "-c:a", "aac",
                "-b:a", "128k", "-movflags", "+faststart", str(audio)])
    segments = []
    clock = 0.0
    frame_position = 0
    for index, (chunk, duration) in enumerate(zip(chunks, durations)):
        pages = panels(chunk["text"])
        weights = [sum(len(line) for line in page) for page in pages]
        for panel_index, lines in enumerate(pages):
            if store.is_canceled(document["id"]):
                raise InterruptedError("Process canceled.")
            directory = work / f"{index:06}-{panel_index:02}"
            directory.mkdir(exist_ok=True)
            background = directory / "scene.png"
            scene(background, document, chunk, lines)
            clock += duration * weights[panel_index] / sum(weights)
            end_frame = max(frame_position + 1, round(clock * 24))
            frames = end_frame - frame_position
            frame_position = end_frame
            segment = directory / "video.mp4"
            avatar = store.file_path(avatars[chunk["mood"]])
            run_ffmpeg(["-loop", "1", "-i", str(background), *avatar_input(avatar, directory),
                "-filter_complex", ("[1:v]scale=430:590:force_original_aspect_ratio=decrease,setsar=1[avatar];"
                "[0:v][avatar]overlay=x=40+(430-overlay_w)/2:y=92+(590-overlay_h),format=yuv420p[v]"),
                "-map", "[v]", "-an", "-r", "24", "-frames:v", str(frames),
                "-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-threads", "2", str(segment)])
            segments.append(segment)
        store.update_document(document["id"], progress=len(chunks) + index + 1)
    video_list = work / "video.txt"
    video_list.write_text("".join(f"file '{p.relative_to(work)}'\n" for p in segments))
    video = root / "video.part.mp4"
    run_ffmpeg(["-f", "concat", "-safe", "0", "-i", str(video_list), "-i", str(audio),
                "-map", "0:v:0", "-map", "1:a:0", "-c", "copy", "-shortest", "-movflags", "+faststart", str(video)])
    if store.is_canceled(document["id"]):
        raise InterruptedError("Process canceled.")
    for temporary, name, kind in ((audio, "audio.mp4", "audio"), (video, "video.mp4", "video")):
        target = root / name
        temporary.replace(target)
        store.add_artifact(document["id"], kind, target)
