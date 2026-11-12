"""Budget: no reply may use more than MAX_TOKENS_PER_REPLY tokens (default 3000).

The count is prompt + completion tokens as reported by the bot in `usage`. A
reply with no usage figure fails, because the budget cannot be checked. Long
conversations and the 25,000-character message are the cases to watch: the
bot has to trim history and cap input to stay under the limit.
"""
import pytest

from botsuite.limits import budget_problems


def test_replies_stay_within_token_budget(store, settings, conversation_case):
    persona_id, run = conversation_case
    problems = budget_problems(store.conversation(persona_id, run), settings.max_tokens_per_reply)
    if problems:
        pytest.fail(f"{persona_id} run {run}: {len(problems)} reply(ies) over budget\n" + "\n".join(problems),
                    pytrace=False)
