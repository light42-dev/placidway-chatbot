"""Consistency: the same conversation played several times must agree.

Runs agree on a turn when every check gives the same verdict and the reply
states the same dollar amounts. Wording may differ. Set CONSISTENCY_AMOUNTS=0
to compare verdicts only.
"""
import pytest

from botsuite.consistency import compare_runs


def test_runs_agree(store, settings, persona_id):
    if settings.runs < 2:
        pytest.skip("consistency needs --runs 2 or more")
    differences = compare_runs(store.all_runs(persona_id), settings.compare_amounts)
    if differences:
        pytest.fail(f"{len(differences)} turn(s) changed between runs:\n" + "\n".join(differences),
                    pytrace=False)
