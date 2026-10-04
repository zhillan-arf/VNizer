import os
import secrets
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv


@dataclass
class Config:
    data_root: Path = field(default_factory=lambda: Path("data").resolve())
    username: str = ""
    password: str = ""
    secret: str = field(default_factory=lambda: secrets.token_hex(32))
    secure_cookie: bool = False
    max_file_bytes: int = 100 * 1024 * 1024
    max_files: int = 20
    max_pages: int = 2000

    @classmethod
    def from_env(cls):
        load_dotenv()
        username = os.getenv("VNIZER_USERNAME", "")
        password = os.getenv("VNIZER_PASSWORD", "")
        secret = os.getenv("VNIZER_SESSION_SECRET", "")
        if bool(username) != bool(password):
            raise ValueError("Set both VNIZER_USERNAME and VNIZER_PASSWORD, or leave both empty.")
        if username and len(secret) < 32:
            raise ValueError("VNIZER_SESSION_SECRET must contain at least 32 characters.")
        return cls(
            data_root=Path(os.getenv("VNIZER_DATA_ROOT", "data")).resolve(),
            username=username,
            password=password,
            secret=secret or secrets.token_hex(32),
            secure_cookie=os.getenv("VNIZER_SECURE_COOKIE", "false").lower() == "true",
        )


def initial_settings():
    tts_type = os.getenv("VNIZER_TTS_TYPE", "qwen")
    if tts_type not in ("qwen", "supertonic"):
        raise ValueError("VNIZER_TTS_TYPE must be qwen or supertonic.")
    return {
        "tts_type": tts_type,
        "ftt_url": os.getenv("VNIZER_FTT_URL", "http://10.12.1.193:1812"),
        "ftt_model": os.getenv("VNIZER_FTT_MODEL", ""),
        "ftt_api_key": os.getenv("VNIZER_FTT_API_KEY", ""),
        "tts_url": os.getenv("VNIZER_TTS_URL", "http://127.0.0.1:1813"),
        "tts_api_key": os.getenv("VNIZER_TTS_API_KEY", ""),
        "speaker": os.getenv("VNIZER_SPEAKER", "F1" if tts_type == "supertonic" else "Ryan"),
        "language": os.getenv("VNIZER_LANGUAGE", "English"),
    }
