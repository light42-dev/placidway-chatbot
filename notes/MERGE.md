# Merge into develop: what was done and what is verified

All 20 persona branches are merged into `develop`. The four chained branches
(T01, E01, E02, E03) merged cleanly. The other sixteen had each edited the
same shared files (the prompt, retrieval, the wiring in `bot/chat.py`), so
each merge brought in that branch's new modules and notes, and one
consolidation commit then integrated every branch's shared-file edits by hand.

## What is verified

| Check | Result |
|---|---|
| `pytest tests/test_suite_selfcheck.py` | 57 passed |
| `python scripts/offline_replay.py` (stand-in model, all 20 personas) | every turn passes; largest prompt about 2,600 tokens by a 4-characters-per-token estimate |
| Live `pytest -k T01 --runs 1` on the merged code | 9 passed, 1 skipped; slowest reply 1.53 s; largest reply 2,721 tokens |
| `pytest tests/test_bot_amounts.py` (added with `bot/amounts.py`) | 38 passed |
| Live `pytest -k "E05 or T03" --runs 1`, after `bot/amounts.py` | E05: 7 of 7 turns. T03: 5 of 6; the trick turn was answered in English (see below) |

**Not verified:** apart from T01, E05 and T03, no persona has been run live on the merged code. The
offline replay feeds each turn's reference reply through the bot, so it shows
that retrieval and the code after the model keep a correct reply correct. It
does not show what a real model will write. E04 to E07 and T02 to T13 have
never been run live at all; see their notes files for the turns at risk.

## Things to watch on the first live runs

- **Token budget.** The largest live reply was 2,721 of 3,000 tokens. The merged
  prompt is about 210 tokens longer than before the merge, and the passage
  budget (`CONTEXT_CHARS`) was cut from 4,800 to 4,200 characters to pay for it.
  Arabic and Spanish text costs more tokens per character.
- **Free-tier quota.** Each Groq model allows about 90 replies a day; a full
  run is 363 requests. See `notes/E02.md`.
- **T03, trick turn in English.** Asked in Spanish about "5 mil dolares", gpt-oss-120b
  answers "I can't confirm ..." in English and fails the language check. It did so
  before and after `bot/amounts.py`. The rules give the refusal wording in English
  and Arabic only.
- **Passage markers in replies.** gpt-oss-120b sometimes writes "【2】" inside a reply
  (seen live in T03). `bot/citations.py` only removes the final "USED:" line.
- **Subject changes.** The branch rule that dropped the page focus by comparing
  match scores fired on ordinary follow-ups from other personas ("tell me the
  November price"), so it was replaced by explicit phrases ("forget that",
  "different question"). See `bot/retrieval/focus.py`.

## Duplicates that were merged into one

| Was (branch modules) | Now |
|---|---|
| Six "add a free-quote line" guards (T05, T06, T08, T09, T11, T13) and two "add a doctor line" guards (T02, T09) | `bot/guards/pointers.py`, which also adds the line in Spanish, French or Arabic |
| Five "recall trimmed messages" helpers (T02, T03, T08, T12, T13) and E01's earlier-prices recall | `bot/history.py` |
| Two foreign-currency filters (T06, T07), T11's unlisted-price filter, E03's price guard | `bot/guards/prices.py` |
| E04's link and contact scrubber, T13's phone and email masking | `bot/guards/contacts.py` |
| Four citation fallbacks (T02, T04, T05, T09) | `bot/citations.py` |
| Focus-page rules from T02, T04, T05, T10 | `bot/retrieval/focus.py` |
| Three language detectors (E05, T13, and the pointer guards) | `bot/language.py` |
| Three dollar-amount parsers (E03 prices, E05 injection, E07 documents), two lists of the prices on the pages, two ways of masking an amount | `bot/amounts.py` |

The per-persona notes files still use the branch-time module names.

## One reader for dollar amounts (`bot/amounts.py`)

The price, injection and document guards each had their own pattern for a
dollar amount, and they disagreed: one did not know "9 000$" or "5 mil
dolares", another did not know "$18 995". They now share one. On every page
line, persona message, reference reply and recorded live reply (1,731 texts)
it finds exactly the amounts the grader's own parser finds.

What changed in behaviour, on purpose:

- **Listed means a price on the pages.** The price guard used to accept any
  number that appears on a page, so "$7" or "$2024" passed. Now only amounts
  the pages state as dollar amounts pass.
- **A kept amount is written with commas.** A model wrote "$18 995" with a
  no-break space; the grader reads that as $18 and fails the reply. Such an
  amount is now rewritten as "$18,995".
- **More ways of writing a figure are recognised:** "9 000$" (T12) and "5 mil
  dolares" (T03). Those conversations now get the same prompt note and the
  same hiding as "$12k" in T01. The note ends with a reminder to answer in the
  user's language: without it, T03 answered two later turns in English.
- **A hidden amount reads "that amount" in the reply's language** ("esa
  cifra", "ce montant"), also where the injection guard used "[unlisted amount]".
- **Conversions are removed before unlisted amounts are hidden**, and a sentence
  that also states a dollar price keeps it. Before, "about C$26,000" became
  "about Cthat amount", and "$18,995, or about £15,000" lost the whole sentence.
- **The document guard no longer repeats the user's figure** when it refuses to
  put it in a table, so the amounts in a reply cannot differ between runs.

## Chat page, Vercel setup and the figure check

- `public/index.html` is a one-file chat page; `python -m bot.serve` serves it
  locally and it was tried in a browser with a live question. `vercel.json` and
  `.vercelignore` are written but **no deployment has been made**.
- `bot/guards/figures.py` drops a reply sentence that states a number (10 or
  more) found in no retrieved passage and nowhere in the conversation. On 243
  recorded live replies it would have removed nothing. It makes no second model
  call, because that would double the tokens a reply costs.
- That check exposed a retrieval gap in T10 `compare` ("is it cheaper in turkey
  or mexico"): two long FAQ passages about costs outranked the table of clinic
  prices, which then did not fit. Passages that state a price now get a bonus
  when the newest message asks about cost (`PRICE_BONUS` in
  `bot/retrieval/index.py`). The offline replay passes all 20 personas again,
  and one other missed page (E04) is now retrieved too. Not run live.

## Still open

- Three coarse "does this text mention money" tests remain (search tokens in
  `bot/retrieval/index.py`, recall in `bot/history.py`, the crisis reply). They
  read no values and are broader on purpose, so they do not use `bot/amounts.py`.
- The rate limit and reply cache are in memory, so on Vercel they only cover
  requests that reach the same warm instance.
- `api/chat.py` has not been deployed.
