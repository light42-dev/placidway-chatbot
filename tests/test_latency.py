"""Latency: no reply may take longer than MAX_LATENCY_S (default 5 seconds).

Time is measured from sending the request to receiving the full response. The
pause the suite inserts between requests is not counted. Median, 95th
percentile and slowest reply are printed in the run summary.
"""
import pytest

from botsuite.limits import slow_turns


def test_replies_are_fast_enough(store, settings, conversation_case):
    persona_id, run = conversation_case
    problems = slow_turns(store.conversation(persona_id, run), settings.max_latency_s)
    if problems:
        pytest.fail(f"{persona_id} run {run}: {len(problems)} slow reply(ies)\n" + "\n".join(problems),
                    pytrace=False)
