"""Shared setup: settings, the lazy conversation store, and the report."""
from __future__ import annotations

import os
from dataclasses import asdict, dataclass
from pathlib import Path

import pytest

from botsuite.client import BotClient
from botsuite.report import summarize, write_reports
from botsuite.runner import ConversationResult, Runner
from botsuite.scenarios import get_persona, load_personas

ROOT = Path(__file__).resolve().parent.parent


def _load_env_file(path: Path) -> None:
    """Read KEY=value lines from .env without overriding real environment variables."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


_load_env_file(ROOT / ".env")


@dataclass
class Settings:
    bot_url: str
    runs: int
    run_abuse: bool
    max_latency_s: float
    max_tokens_per_reply: int
    timeout_s: float
    min_interval_s: float
    compare_amounts: bool
    canary: str | None


def pytest_addoption(parser):
    group = parser.getgroup("bot")
    group.addoption("--runs", type=int, default=int(os.environ.get("RUNS", "3")),
                    help="how many times to play each conversation (default 3)")
    group.addoption("--run-abuse", action="store_true",
                    help="also send the rapid-fire burst (spends API quota)")


def _settings(config) -> Settings:
    env = os.environ.get
    return Settings(
        bot_url=env("BOT_URL", ""),
        runs=config.getoption("--runs"),
        run_abuse=config.getoption("--run-abuse"),
        max_latency_s=float(env("MAX_LATENCY_S", "5")),
        max_tokens_per_reply=int(env("MAX_TOKENS_PER_REPLY", "3000")),
        timeout_s=float(env("BOT_TIMEOUT_S", "30")),
        min_interval_s=float(env("BOT_MIN_INTERVAL_S", "2")),
        compare_amounts=env("CONSISTENCY_AMOUNTS", "1") != "0",
        canary=env("SYSTEM_PROMPT_CANARY") or None,
    )


class Store:
    """Plays each conversation the first time a test asks for it, then reuses it."""

    def __init__(self, settings: Settings):
        self.settings = settings
        client = BotClient(settings.bot_url, settings.timeout_s, settings.min_interval_s)
        self.runner = Runner(client, run_abuse=settings.run_abuse, canary=settings.canary)
        self._done: dict[tuple[str, int], ConversationResult] = {}

    def conversation(self, persona_id: str, run: int) -> ConversationResult:
        key = (persona_id, run)
        if key not in self._done:
            self._done[key] = self.runner.run_conversation(get_persona(persona_id), run)
        return self._done[key]

    def all_runs(self, persona_id: str) -> list[ConversationResult]:
        return [self.conversation(persona_id, run) for run in range(1, self.settings.runs + 1)]

    @property
    def conversations(self) -> list[ConversationResult]:
        return list(self._done.values())


_STORE: Store | None = None


@pytest.fixture(scope="session")
def settings(pytestconfig) -> Settings:
    return _settings(pytestconfig)


@pytest.fixture(scope="session")
def store(settings) -> Store:
    global _STORE
    if not settings.bot_url:
        pytest.skip("BOT_URL is not set: put the bot's chat endpoint in .env to run the live tests")
    if _STORE is None:
        _STORE = Store(settings)
    return _STORE


def pytest_generate_tests(metafunc):
    runs = range(1, metafunc.config.getoption("--runs") + 1)
    personas = load_personas()
    if "turn_case" in metafunc.fixturenames:
        cases = [(p.id, run, i) for p in personas for run in runs for i in range(len(p.turns))]
        ids = [f"{p.id}-run{run}-{i + 1:02d}_{p.turns[i].id}"
               for p in personas for run in runs for i in range(len(p.turns))]
        metafunc.parametrize("turn_case", cases, ids=ids)
    if "conversation_case" in metafunc.fixturenames:
        cases = [(p.id, run) for p in personas for run in runs]
        metafunc.parametrize("conversation_case", cases, ids=[f"{pid}-run{run}" for pid, run in cases])
    if "persona_id" in metafunc.fixturenames:
        metafunc.parametrize("persona_id", [p.id for p in personas])


def pytest_terminal_summary(terminalreporter, config):
    if _STORE is None or not _STORE.conversations:
        return
    settings = asdict(_STORE.settings)
    transcript = write_reports(_STORE.conversations, ROOT / "reports", settings)
    summary = summarize(_STORE.conversations)
    terminalreporter.section("bot run summary")
    terminalreporter.write_line(f"requests sent: {_STORE.runner.client.requests_sent}")
    for key, value in summary.items():
        terminalreporter.write_line(f"{key}: {value}")
    terminalreporter.write_line(f"transcript: {transcript}")
