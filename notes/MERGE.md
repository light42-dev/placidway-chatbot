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

**Not verified:** no other persona has been run live on the merged code. The
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

The per-persona notes files still use the branch-time module names.

## Still open

- `bot/guards/injection.py` keeps its own amount parser and per-page price
  list, separate from `bot/guards/prices.py`; they could share one.
- The rate limit and reply cache are in memory, so on Vercel they only cover
  requests that reach the same warm instance.
- `api/chat.py` has not been deployed.
