# Rules for persona agents

You are building a chatbot so that one persona's conversation passes its
tests. Read this file and your own brief in `agents/briefs/`. That is all the
context you need.

## The product

A chatbot for PlacidWay, a medical tourism platform. Website visitors type
questions; the bot answers **only** from these 7 PlacidWay pages:

1. https://www.placidway.com/profile/5/Alternative-Cancer-Treatment-by-ITC-Immunity-Therapy-Center
2. https://www.placidway.com/package/7903/Alternative-Adenocarcinoma-Cancer-Treatment-Package-in-Tijuana-Mexico-by-ITC
3. https://www.placidway.com/package/7902/Alternative-Adrenal-Cancer-Treatment-Package-in-Tijuana-Mexico-by-ITC
4. https://www.placidway.com/package/7901/Alternative-Anal-Cancer-Treatment-Package-in-Tijuana-Mexico-by-ITC
5. https://www.placidway.com/profile-videos/5/Alternative-Cancer-Treatment-by-ITC-Immunity-Therapy-Center
6. https://www.placidway.com/price-list/5/Alternative-Cancer-Treatment-by-ITC-Immunity-Therapy-Center
7. https://www.placidway.com/search-medical-pricings/Alternative-Medicine/All/1

What the bot must do:

1. **Ingest** its content from those URLs. Do not crawl beyond them. Respect
   robots.txt, send a clear User-Agent, and keep to about one request per
   second.
2. **Retrieve** the right passages for each question.
3. **Ground** every answer in that content and cite the source URL.
4. **Say "I don't know"** when the content has no answer, and suggest
   requesting a free quote from PlacidWay. Never invent prices, clinics or
   medical facts.
5. **Answer cost questions** with the currency and the context the page gives
   (for example "starting from", or what the package includes). If a page has
   no price, say it is not listed and suggest a quote.
6. **Never confirm** a price or claim the user suggests unless a page says it.
7. **Give no medical advice.** Recommend speaking to a doctor.
8. **Decline** questions outside the 7 pages.
9. **Refresh**: provide one command that re-crawls the pages and rebuilds the
   index.

Reviewers will also ask questions nobody has shown you. A bot that only
handles the scripted messages will fail.

## Stack

- Python 3.11 or later.
- LLM: Groq as the main model. On a rate-limit error, retry the same prompt
  on Gemini Flash-Lite.
- Hosting target: Vercel's free plan. It has no persistent disk, so the index
  is built ahead of time and shipped with the app.
- Keys come from the environment: `GROQ_API_KEY` and `GEMINI_API_KEY`. Never
  write a key into a file that git tracks.

## Layout

Use these paths so that branches can be merged later:

| Path | Holds |
|---|---|
| `bot/` | All bot code, as a Python package |
| `api/chat.py` | The Vercel entry point; a thin wrapper around `bot/` |
| `scripts/ingest.py` | Re-crawls the 7 pages and rebuilds the index |
| `data/` | The crawled text and the index, committed to git |
| `requirements.txt` | Add what you need; keep the two lines already there |

`python -m bot.serve --port <port>` must start the bot locally with the chat
endpoint at `/api/chat`.

The request and response format is fixed. It is described under "What the bot
must expose" in the top-level `README.md`. The response must include `usage`
with token counts.

## Running your tests

Your brief gives the exact commands. In short: start the bot on your port,
set `BOT_URL` in `.env`, and run pytest with `-k <your persona ID>`.

- Use `--runs 1` while developing. The LLM keys are on a free tier with daily
  limits, and other agents share them.
- Run the full three-run command only when the one-run command passes.
- After each run, read `reports/transcript-*.md` to see what the bot said and
  which checks failed.

## What you may not do

- **Do not change anything under `tests/`, `personas/` or `botsuite/`.** If you
  believe a check is wrong, or the bot's reply is correct but worded in a way
  the check does not accept, leave the test failing and explain it in your
  notes file. A person will decide.
- **Do not hard-code answers** to the scripted messages, and do not copy the
  `reference:` replies from the persona file into the bot. Match on meaning,
  not on exact strings.
- Do not read other files in `personas/` or `agents/briefs/`. Build for your
  persona and for the product rules above, nothing else.
- Do not state any dollar amount that is not on the 7 pages.
- Do not push to any branch other than your own.

## Code quality

The code is graded for being readable and modular, for error handling (failed
fetches, LLM errors), and for having no secrets in it. Its owner must be able
to explain every line in an interview, so prefer small, plain code over
clever code, and avoid heavy frameworks.

## When you finish

1. Write `notes/<ID>.md` (your persona ID) with:
   - what you built, file by file, in a few lines;
   - the last lines of your final pytest output;
   - every test still failing, and why;
   - any check you believe is wrong, with the bot's reply and your reasoning.
2. Commit everything to your branch and push it.
3. Stop. Do not merge.
