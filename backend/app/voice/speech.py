"""Lazy, serialized subprocess inference. Timeouts terminate owned workers."""

import io
import multiprocessing as mp
import threading
from pathlib import Path

from app.voice.errors import error

MIMES = {"audio/webm", "audio/ogg", "audio/wav", "audio/x-wav", "audio/mp4"}


def decode_audio(raw, mime, seconds):
    import av
    import numpy as np

    try:
        with av.open(io.BytesIO(raw)) as container:
            expected = {
                "audio/webm": "webm",
                "audio/ogg": "ogg",
                "audio/wav": "wav",
                "audio/x-wav": "wav",
                "audio/mp4": "mp4",
            }[mime]
            if expected not in container.format.name:
                raise ValueError("Media content does not match its audio type.")
            if container.duration and container.duration / av.time_base > seconds + 0.5:
                raise ValueError("Recording exceeds the duration limit.")
            resampler = av.AudioResampler(format="s16", layout="mono", rate=16000)
            chunks, samples = [], 0
            for frame in container.decode(audio=0):
                for part in resampler.resample(frame):
                    chunk = part.to_ndarray().flatten()
                    samples += len(chunk)
                    if samples > 16000 * (seconds + 0.5):
                        raise ValueError("Recording exceeds the duration limit.")
                    chunks.append(chunk)
            for part in resampler.resample(None):
                chunks.append(part.to_ndarray().flatten())
            if not chunks:
                raise ValueError("Recording contains no audio.")
            audio = np.concatenate(chunks).astype(np.float32) / 32768.0
            if len(audio) < 1600 or np.max(np.abs(audio)) < 0.003:
                raise ValueError("No intelligible speech detected. Try recording again.")
            return audio
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError("Audio could not be decoded. Record WebM, Ogg, WAV or MP4 audio.") from exc


def speech_worker(pipe, kind, config):
    model = None
    while True:
        try:
            task = pipe.recv()
        except EOFError:
            return
        try:
            if kind == "stt":
                audio = decode_audio(task["audio"], task["mime"], config["seconds"])
                if model is None:
                    import ctranslate2
                    from faster_whisper import WhisperModel

                    device = "cpu"
                    if config["device"] != "cpu":
                        try:
                            if ctranslate2.get_cuda_device_count() > 0:
                                device = "cuda"
                        except Exception:
                            device = "cpu"
                    try:
                        model = WhisperModel(
                            config["whisper"],
                            device=device,
                            compute_type=config["compute"] if device == "cuda" else "int8",
                            cpu_threads=2,
                            num_workers=1,
                            local_files_only=True,
                        )
                    except Exception:
                        model = WhisperModel(
                            config["whisper"],
                            device="cpu",
                            compute_type="int8",
                            cpu_threads=2,
                            num_workers=1,
                            local_files_only=True,
                        )
                segments, info = model.transcribe(
                    audio,
                    language=task["language"] if task["language"] != "auto" else None,
                    beam_size=1,
                    vad_filter=True,
                    condition_on_previous_text=False,
                )
                text = " ".join(
                    part.text.strip() for part in segments if part.no_speech_prob < 0.6
                ).strip()
                if not text:
                    raise ValueError("No intelligible speech detected. Try recording again.")
                if len(text) > 1000:
                    raise ValueError("Transcript is too long. Use a shorter command.")
                result = {"text": text, "language": info.language}
            else:
                import wave

                from piper import PiperVoice, SynthesisConfig

                if model is None:
                    model = PiperVoice.load(
                        config["piper"], config_path=config["piper_config"], use_cuda=False
                    )
                output = io.BytesIO()
                with wave.open(output, "wb") as wav:
                    model.synthesize_wav(
                        task["text"], wav, syn_config=SynthesisConfig(speaker_id=config["speaker"])
                    )
                result = output.getvalue()
                if len(result) > 8388608:
                    raise ValueError("Speech output exceeds its limit.")
            pipe.send((True, result))
        except ValueError as exc:
            pipe.send((False, str(exc)[:200]))
        except Exception:
            pipe.send(
                (False, "Local speech model failed. Check installed models and available memory.")
            )


class SpeechRuntime:
    def __init__(self, settings):
        self.settings = settings
        self.lock = threading.Lock()
        self.workers = {}

    def installed(self, kind):
        if kind == "stt":
            path = Path(self.settings.whisper_model_path)
            return path.is_dir() and all(
                (path / name).is_file() for name in ("model.bin", "config.json", "tokenizer.json")
            )
        return (
            self.settings.voice_tts_enabled
            and Path(self.settings.piper_model_path).is_file()
            and Path(self.settings.piper_config_path).is_file()
        )

    def close(self):
        for process, pipe in self.workers.values():
            pipe.close()
            if process.is_alive():
                process.terminate()
            process.join(timeout=3)
        self.workers.clear()

    def run(self, kind, task):
        if not self.settings.voice_enabled:
            raise error("DISABLED", "Voice processing is disabled.", 503)
        if not self.installed(kind):
            raise error(
                "MODEL_MISSING",
                "Local speech model is not installed. Follow Windows model setup.",
                503,
            )
        if not self.lock.acquire(blocking=False):
            raise error("BUSY", "Local speech processing is busy. Try again shortly.", 429)
        try:
            if kind not in self.workers:
                ctx = mp.get_context("spawn")
                parent, child = ctx.Pipe()
                s = self.settings
                config = {
                    "whisper": str(Path(s.whisper_model_path).resolve()),
                    "device": s.whisper_device,
                    "compute": s.whisper_compute_type,
                    "seconds": s.voice_max_recording_seconds,
                    "piper": str(Path(s.piper_model_path).resolve()),
                    "piper_config": str(Path(s.piper_config_path).resolve()),
                    "speaker": s.piper_speaker_id,
                }
                process = ctx.Process(target=speech_worker, args=(child, kind, config), daemon=True)
                process.start()
                child.close()
                self.workers[kind] = (process, parent)
            process, pipe = self.workers[kind]
            pipe.send(task)
            if not pipe.poll(self.settings.voice_timeout_seconds):
                self.close()
                raise error(
                    "TIMEOUT", "Local speech processing timed out. Try a shorter recording.", 504
                )
            ok, result = pipe.recv()
            if not ok:
                raise error("SPEECH_FAILED", result)
            return result
        except (EOFError, BrokenPipeError, OSError) as exc:
            self.close()
            raise error(
                "SPEECH_FAILED", "Local speech worker stopped. Retry after checking memory.", 503
            ) from exc
        finally:
            self.lock.release()
