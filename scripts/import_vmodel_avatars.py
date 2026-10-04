#!/usr/bin/env python3
"""Encode rendered VModel frames and select the local mood assets."""

import argparse
import json
import shutil
from pathlib import Path

from PIL import Image

from vnizer.avatars import add_avatar, seed_avatars
from vnizer.config import Config
from vnizer.files import digest_file
from vnizer.store import MOODS, Store


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("frames", type=Path)
    parser.add_argument("--pack", type=Path, default=Path("/data-model/zhillan/VNizer/avatars/ene"))
    args = parser.parse_args()
    store = Store(Config.from_env().data_root)
    seed_avatars(store)
    args.pack.mkdir(parents=True, exist_ok=True)
    inventory = json.loads((args.frames / "source.json").read_text())
    notices = Path(inventory["source"]).parents[3] / "ops/resources/ENE/Readmes"
    if notices.is_dir():
        shutil.copytree(notices, args.pack / "source-notices", dirs_exist_ok=True)
    inventory["assets"] = []
    for mood in MOODS:
        frames = []
        for index in range(4):
            with Image.open(args.frames / mood / f"{index:02}.png") as image:
                frames.append(image.convert("RGBA"))
        path = args.pack / f"{mood}.webp"
        frames[0].save(path, format="WEBP", save_all=True, append_images=frames[1:],
                       duration=[300, 180, 100, 220], loop=0, lossless=True)
        avatar_id = add_avatar(store, path, "Ene · " + mood, mood)
        with store.connect() as db:
            db.execute("UPDATE avatars SET selected=0 WHERE mood=?", (mood,))
            db.execute("UPDATE avatars SET selected=1 WHERE id=?", (avatar_id,))
        inventory["assets"].append({"mood": mood, "file": path.name, "sha256": digest_file(path),
                                    "bytes": path.stat().st_size})
    (args.pack / "inventory.json").write_text(json.dumps(inventory, indent=2) + "\n")
    print(f"Imported five mood assets into {store.root}")


if __name__ == "__main__":
    main()
