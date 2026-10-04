#!/usr/bin/env python3
"""Download immutable model revisions and verify upstream file hashes."""

import argparse
import hashlib
import json
import urllib.request
from pathlib import Path

REPOSITORIES = (
    "Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice",
    "Qwen/Qwen3-TTS-Tokenizer-12Hz",
)


def request_json(url):
    with urllib.request.urlopen(url, timeout=60) as response:
        return json.load(response)


def file_hash(path, algorithm="sha256", git_blob=False):
    digest = hashlib.new(algorithm)
    if git_blob:
        digest.update(f"blob {path.stat().st_size}\0".encode())
    with path.open("rb") as source:
        while block := source.read(8 * 1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def download(root, repository):
    info = request_json(f"https://huggingface.co/api/models/{repository}?blobs=true")
    revision = info["sha"]
    target = root / repository.split("/")[-1]
    target.mkdir(parents=True, exist_ok=True)
    inventory = {"repository": repository, "revision": revision, "files": []}
    for item in info["siblings"]:
        name = item["rfilename"]
        path = (target / name).resolve()
        if not path.is_relative_to(target.resolve()):
            raise ValueError("The model contains an invalid file path.")
        path.parent.mkdir(parents=True, exist_ok=True)
        lfs = item.get("lfs")
        expected = lfs["sha256"] if lfs else item["blobId"]
        algorithm = "sha256" if lfs else "sha1"
        if not path.exists() or file_hash(path, algorithm, not lfs) != expected:
            partial = path.with_name(path.name + ".part")
            print(f"Download {repository}/{name}", flush=True)
            url = f"https://huggingface.co/{repository}/resolve/{revision}/{name}"
            with urllib.request.urlopen(url, timeout=120) as response, partial.open("wb") as output:
                while block := response.read(8 * 1024 * 1024):
                    output.write(block)
            if file_hash(partial, algorithm, not lfs) != expected:
                raise ValueError(f"Model checksum mismatch: {name}")
            partial.replace(path)
        inventory["files"].append({"path": name, "bytes": path.stat().st_size,
                                   "sha256": file_hash(path), "upstream_hash": expected})
        print(f"Verified {name}", flush=True)
    manifest = target / "vnizer-inventory.json"
    manifest.write_text(json.dumps(inventory, indent=2) + "\n")
    return inventory


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("/data-model/zhillan/VNizer"))
    args = parser.parse_args()
    args.root.mkdir(parents=True, exist_ok=True)
    for repository in REPOSITORIES:
        download(args.root, repository)


if __name__ == "__main__":
    main()
