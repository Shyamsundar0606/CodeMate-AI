"""Run the durable local investigation worker, separately from FastAPI."""

import json
import logging
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.ai.worker import InvestigationWorker
from app.core.config import Settings
from app.core.logging import protect_external_access_logs
from app.core.observability import configure_logging
from app.db.session import build_engine, build_session_factory
from app.integrations.github.client import GitHubClient
from app.integrations.ollama.client import OllamaClient


def main():
    settings = Settings()
    protect_external_access_logs()
    configure_logging(settings.app_env, service="codemate-ai-worker")
    engine = build_engine(settings)
    github = GitHubClient(settings)
    ollama = OllamaClient(settings)
    worker = InvestigationWorker(settings, build_session_factory(engine), engine, github, ollama)
    try:
        while True:
            try:
                worked = worker.tick()
            except Exception:
                logging.getLogger("codemate.ai").error(
                    json.dumps({"event": "worker_unavailable", "category": "dependency"})
                )
                worked = False
            if not worked:
                time.sleep(2)
    except KeyboardInterrupt:
        pass
    finally:
        github.close()
        ollama.close()
        engine.dispose()


if __name__ == "__main__":
    main()
