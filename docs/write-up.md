# Write-up: known limitations and what I would do with another week

## Known limitations

- **Free-tier quota.** Each Groq model allows about 200,000 tokens a day, roughly 80 to 90 replies. The bot tries three Groq models in turn and then Gemini Flash-Lite, which answers in 3 to 8 seconds instead of about 1. Heavy testing in one day will slow it down.
- **Keyword retrieval.** Passages are found by keyword search (BM25) in English. Spanish and Arabic work through word lists; other languages, and words missing from those lists, retrieve poorly.
- **Comparisons can be incomplete.** The bot refuses a like-for-like comparison when procedures differ and quotes only listed prices, but it does not always list every clinic for a country.
- **Limited live testing.** The 8 assessment questions pass on the deployed bot (`docs/test-results.md`), from a single run. Of my 20 test personas, 5 pass live and 14 have only been checked offline with a stand-in model.
- **Rate limit and cache are in memory**, so on serverless hosting they only cover requests that reach the same warm instance.
- **Checks cover figures, not wording.** Code verifies every price against what the model was shown and builds the source links itself, but it does not check each sentence against a quote from the page.
- **Refresh is untested in CI.** `python scripts/ingest.py` works locally; the weekly GitHub Action has not had its first run.
- **Not built:** lead capture and a log of unanswered questions.

## With another week

1. Run all 20 personas against the live bot several times and fix what fails, then add PlacidWay's own hidden-question style cases.
2. Log every "I don't know" answer with its question, to show content gaps, and offer to take a name and email when a visitor asks for a quote.
3. Build comparison answers in code: read the price tables into rows (clinic, country, procedure, price) so the lowest listed price per country is computed, not left to the model.
4. Add multilingual embeddings alongside keyword search, so any language retrieves well without word lists.
5. Move the rate limit and cache to a small key-value store, and add an alert when the bot falls back to the slow model.
