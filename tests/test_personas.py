"""Correctness: every turn of every persona conversation, on every run.

One test per turn, named <persona>-run<n>-<turn number>_<turn id>, for example
T01-run1-05_trick_12k. The whole conversation is played in order with its
history, so a turn tagged `recall` only passes if the bot remembers what was
said before an `abrupt` change of topic.
"""
import pytest

from botsuite.scenarios import get_persona


def _shorten(text: str, limit: int = 700) -> str:
    return text if len(text) <= limit else text[:limit] + " …"


def test_turn(store, turn_case):
    persona_id, run, index = turn_case
    turn = store.conversation(persona_id, run).turns[index]
    if turn.skipped:
        pytest.skip(turn.skipped)
    if turn.passed:
        return

    persona = get_persona(persona_id)
    lines = [f"{persona.id} {persona.name}: {persona.label}",
             f"turn {index + 1} ({turn.turn_id}), tags: {', '.join(turn.tags) or 'none'}",
             f"USER: {turn.user}"]
    if turn.burst:
        lines.append(f"BURST: {turn.burst}")
    else:
        lines.append(f"BOT (HTTP {turn.status}): {_shorten(turn.reply) or turn.error}")
    lines += [f"FAILED {c['name']}: {c['detail']}" for c in turn.failures]
    pytest.fail("\n".join(lines), pytrace=False)
