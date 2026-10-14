"""Explicit real-model smoke test; never included in deterministic CI."""

import argparse
import json
from pathlib import Path

from app.core.config import Settings
from app.integrations.ollama.client import OllamaClient
from app.voice.agent import interpret
from app.voice.speech import SpeechRuntime

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--investigate", action="store_true")
    args = parser.parse_args()
    settings = Settings()
    speech = SpeechRuntime(settings)
    output = Path(".voice-verification")
    output.mkdir(exist_ok=True)
    try:
        text = (
            "CodeMate, analyze the latest failed pipeline."
            if args.investigate
            else "CodeMate, open my GitHub repositories."
        )
        audio = speech.run("tts", {"text": text})
        (output / ("investigate.wav" if args.investigate else "command.wav")).write_bytes(audio)
        transcript = speech.run("stt", {"audio": audio, "mime": "audio/wav", "language": "en"})
        print(
            json.dumps(
                {"piper_bytes": len(audio), "transcription": transcript, "synthetic_input": True}
            )
        )
        ollama = OllamaClient(settings)
        try:
            intent = interpret(ollama, "Take me to the page where my user profile is shown.")
            print(json.dumps({"real_ollama_intent": intent.model_dump()}))
        finally:
            ollama.close()
    finally:
        speech.close()
