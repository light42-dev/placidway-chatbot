# Status: what is verified and what is not

## Verified

| Check | Result |
|---|---|
| `pytest tests/test_suite_selfcheck.py tests/test_bot_amounts.py` (no bot or API key needed) | 99 passed |
| `python scripts/offline_replay.py` (all 20 personas, stand-in model) | every turn passes |
| Live, three runs each: T01, E01 | all turns pass; latency and consistency pass |
| Live, three runs: E02 | all turns pass; latency failed because the slow fallback model answered |
| Live, one run each: E05, T03 | all turns pass |
| Chat page (`public/index.html`), opened in a browser against the local server | works at desktop and phone width |

The bot's reading of dollar amounts agrees with the test suite's own parser on
every page line, persona message and reference reply (`tests/test_bot_amounts.py`).

The offline replay feeds each turn's reference reply through the bot. It shows
that retrieval and the code after the model keep a correct reply correct. It
does not show what a real model will write.

## Not verified

- **Fourteen personas have never been run against a live model:** E04, E06, E07,
  T02, T04 to T13. E03 was run live before its last fix and failed one turn then.
- **No deployment has been made.** `vercel.json` and `api/chat.py` have only been
  exercised through the local server.
- **The retry** (the model is asked once more when it invents a figure) has only
  been run with a stand-in model. On 243 recorded live replies it would not have fired.
- **The weekly refresh** (`.github/workflows/refresh.yml`) has never run. GitHub
  runs scheduled workflows from the default branch only. Whether placidway.com
  answers GitHub's servers is unknown.

## Known limits

- **Free-tier quota.** Each Groq model allows 200,000 tokens a day (about 80
  replies) and 8,000 a minute. The bot tries three Groq models, then Gemini
  Flash-Lite, which took 3 to 8 seconds per reply in testing. A full test run is
  363 requests, more than one day of fast replies. Run the suite with
  `BOT_MIN_INTERVAL_S=16`.
- **Rate limit and reply cache are in memory.** On serverless hosting they only
  cover requests that reach the same warm instance.
- **Retrieval is keyword search in English.** Spanish and Arabic questions work
  through word lists in `bot/retrieval/spanish.py` and `arabic.py`; other
  languages, and words missing from those lists, will retrieve poorly.
- **Passage budget.** About 4,200 characters of passages fit in a prompt. A
  typical reply uses about 2,400 tokens; the limit in the tests is 6,000 so that
  a retried reply also passes.
- **No exact-quote check.** Code verifies prices and other figures against what
  the model was shown, and builds the source links itself, but does not check
  the wording of each claim against a quote.
- **Three coarse "does this text mention money" tests** (search tokens, recall,
  the crisis reply) do not use `bot/amounts.py`; they read no values and are
  broader on purpose.
- **Some model names are retired on these keys:** `llama-3.1-8b-instant` (Groq)
  and `gemini-2.5-flash`. The models in use are set in `bot/config.py`.
