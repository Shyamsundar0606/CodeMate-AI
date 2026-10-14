"""Explicit opt-in model download from official repositories, never run by CI."""

import argparse
import hashlib
import json
from pathlib import Path

import httpx
from huggingface_hub import HfApi, snapshot_download

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--download", action="store_true", required=True)
    parser.add_argument("--whisper", choices=["base", "small"], default="base")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1] / "models"
    root.mkdir(exist_ok=True)
    api = HfApi()
    repo = "Systran/faster-whisper-" + args.whisper
    revision = api.model_info(repo).sha
    snapshot_download(
        repo,
        revision=revision,
        local_dir=root / ("whisper-" + args.whisper),
        allow_patterns=[
            "model.bin",
            "config.json",
            "tokenizer.json",
            "vocabulary.*",
            "preprocessor_config.json",
        ],
    )
    voice_repo = "rhasspy/piper-voices"
    voice_revision = api.model_info(voice_repo).sha
    prefix = "en/en_US/ljspeech/medium/"
    names = [
        "en_US-ljspeech-medium.onnx",
        "en_US-ljspeech-medium.onnx.json",
        "MODEL_CARD",
        "README.md",
    ]
    hashes = {}
    for name in names:
        source_path = name if name == "README.md" else prefix + name
        url = f"https://huggingface.co/{voice_repo}/resolve/{voice_revision}/{source_path}"
        local_name = {
            "MODEL_CARD": "ljspeech-MODEL_CARD.txt",
            "README.md": "piper-voices-README.md",
        }.get(name, name)
        path = root / local_name
        with httpx.stream("GET", url, follow_redirects=True, timeout=120) as response:
            response.raise_for_status()
            with path.open("wb") as output:
                for data in response.iter_bytes():
                    output.write(data)
        hashes[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    (root / "voice-model-manifest.json").write_text(
        json.dumps(
            {
                "whisper_repository": repo,
                "whisper_revision": revision,
                "piper_repository": voice_repo,
                "piper_revision": voice_revision,
                "sha256": hashes,
            },
            indent=2,
        )
    )
    print(
        "Official models downloaded; pinned revisions and hashes are in "
        "models/voice-model-manifest.json"
    )
