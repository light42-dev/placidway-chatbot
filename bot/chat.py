"""Turn a conversation into a grounded answer.

    conversation -> early exits (crisis, abuse) -> retrieve passages -> prompt
                 -> model (asked again once if it invents a figure)
                 -> checks on the reply -> citation

Every step lives in its own module; this file only puts them in order.
"""
from __future__ import annotations

from . import config, history, prompt
from .citations import cite, split_used_line
from .guards import abuse, contacts, crisis, documents, figures, injection, pointers, prices
from .llm import Completion, LLMError, complete
from .pages import PAGES
from .retrieval import Passage, focus_page, load_index, pin_inclusions, pin_price_rows, video_passage

NO_TOKENS = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}


def _reply(text: str, sources: list[str], completion: Completion) -> dict:
    return {
        "answer": text,
        "sources": sources,
        "usage": {"prompt_tokens": completion.prompt_tokens,
                  "completion_tokens": completion.completion_tokens,
                  "total_tokens": completion.total_tokens},
        "model": completion.model,
    }


def _crisis_answer(conversation: list[dict]) -> dict:
    """A user who may be at risk gets support and a crisis line, never passages or prices."""
    _, shown = history.split(conversation)
    completion = complete(crisis.CRISIS_PROMPT, shown)
    text, _ = split_used_line(completion.text)
    return _reply(crisis.make_crisis_reply_safe(text), [], completion)


def _last_cited_page(conversation: list[dict]) -> str | None:
    """The page the bot linked to most recently, so follow-ups stay on the same subject."""
    for message in reversed(conversation):
        if message["role"] == "assistant":
            for page in PAGES:
                if page.url in message["content"]:
                    return page.key
    return None


def _find_passages(user_messages: list[str], focus: str | None, videos: Passage | None) -> list[Passage]:
    """Keyword search, plus the cases it handles badly: video titles, price-table rows and inclusion lists."""
    index = load_index()
    budget = config.CONTEXT_CHARS - (len(videos.text) if videos else 0)
    passages = ([videos] if videos else []) + index.search(user_messages, focus, budget)
    passages = pin_price_rows(passages, user_messages, index.passages, focus)
    return pin_inclusions(passages, user_messages[-1], index.passages, focus)


def _ask_model(system: str, shown: list[dict], shown_to_model: str) -> Completion:
    """Ask the model; if its draft states a figure it was not shown, ask once more, naming the figure.

    The second answer is used whatever it says: _check_reply removes anything
    still unsupported. Both calls count towards the tokens reported.
    """
    first = complete(system, shown)
    invented = figures.unsupported(split_used_line(first.text)[0], shown_to_model)
    if not invented:
        return first
    try:
        second = complete(system + prompt.retry_note(invented), shown)
    except LLMError:
        return first                    # no second answer to be had; the checks clean the first
    return Completion(second.text, first.prompt_tokens + second.prompt_tokens,
                      first.completion_tokens + second.completion_tokens, second.model)


def _check_reply(text: str, conversation: list[dict], user_messages: list[str], focus: str | None,
                 shown_to_model: str) -> str:
    """Rules that must hold whatever the model wrote. Order matters: remove first, then add."""
    question = user_messages[-1]
    text = injection.make_reply_safe(text, user_messages, prompt.RULES, focus)
    text = prices.drop_dictated_phrases(text, user_messages)
    text = prices.hide_unlisted_amounts(prices.drop_converted_amounts(text))
    text = figures.drop_unsupported_figures(text, shown_to_model)
    text = prices.restate_listed_prices(text, conversation, user_messages)
    text = contacts.scrub(text)
    text = pointers.add_quote_pointer(text, question)
    return pointers.add_doctor_pointer(text, question)


def answer(messages: list[dict]) -> dict:
    """Build the reply for a conversation. Raises bot.llm.LLMError if no model answers."""
    conversation = history.user_and_bot_messages(messages)
    for message in conversation:                    # the model never sees phone numbers or emails
        message["content"] = contacts.redact(message["content"])
    question = conversation[-1]["content"]

    if crisis.is_crisis(question):
        return _crisis_answer(conversation)
    refusal = abuse.refusal_for(question)
    if refusal:                                     # flooding or bulk extraction: no model call
        return {"answer": refusal, "sources": [], "usage": dict(NO_TOKENS), "model": "none"}

    # Retrieval reads every user message, so the subject is remembered even after older
    # messages are trimmed from what the model is sent. Refused messages have no subject.
    user_messages = [m["content"] for m in conversation
                     if m["role"] == "user" and not abuse.refusal_for(m["content"])]
    focus = focus_page(user_messages, _last_cited_page(conversation))
    videos = video_passage(question)                # "a video about X?" is checked against every title
    passages = _find_passages(user_messages, focus, videos)

    older, shown = history.split(conversation)
    unlisted = prices.unlisted_amounts(user_messages)
    notes = [prompt.unlisted_price_note(unlisted) if unlisted else "",
             injection.security_note(user_messages),
             documents.extra_rules(question),
             prompt.language_note(question)]
    recalled = history.recall(older, question)
    # The passages, what was recalled and the conversation: all a figure in the reply may come from.
    shown_to_model = "\n".join([*(p.text for p in passages), recalled, *(m["content"] for m in conversation)])
    completion = _ask_model(prompt.build(passages, recalled, notes), shown, shown_to_model)

    text, used = split_used_line(completion.text)
    text = _check_reply(text, conversation, user_messages, focus, shown_to_model)
    text, sources = cite(text, used, passages)
    if videos and not sources:                      # a video question is answered from the list of titles
        text, sources = cite(text, [passages.index(videos) + 1], passages)
    text, sources = documents.make_safe(question, text, sources)
    return _reply(text, sources, completion)
