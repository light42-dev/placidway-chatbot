"""Retrieval cases that plain keyword ranking gets wrong. Needs no bot and no API key."""
import pytest

from bot.chat import _find_passages
from bot.retrieval import focus_page, video_passage


def passages_for(*user_messages: str, last_cited: str | None = None):
    messages = list(user_messages)
    focus = focus_page(messages, last_cited)
    return _find_passages(messages, focus, video_passage(messages[-1]))


@pytest.mark.parametrize("question, page", [
    ("What is included in the alternative adenocarcinoma cancer treatment package?", "pkg_adenocarcinoma"),
    ("what does the adrenal cancer package include?", "pkg_adrenal"),
    ("¿Qué incluye el paquete de cáncer anal?", "pkg_anal"),
])
def test_inclusion_question_gets_both_included_sections(question, page):
    found = passages_for(question)
    headings = [p.text.splitlines()[0] for p in found if p.page == page]
    assert any(h.startswith("# Included in the Out-Patient Program") for h in headings)
    assert any(h.startswith("# Included in the In-Patient Program") for h in headings)


def test_inclusion_follow_up_stays_on_the_package_discussed():
    found = passages_for("How much does alternative adenocarcinoma cancer treatment cost in Mexico?",
                         "what does that include?", last_cited="pkg_adenocarcinoma")
    assert found[0].page == "pkg_adenocarcinoma"
    assert found[0].text.startswith("# Included in the")


def test_other_questions_are_not_given_the_inclusion_sections_first():
    found = passages_for("How much does alternative adenocarcinoma cancer treatment cost in Mexico?")
    assert not found[0].text.startswith("# Included in the")
