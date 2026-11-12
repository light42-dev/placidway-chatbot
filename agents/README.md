# Persona branch workflow

How the bot gets built: one agent per persona, each on its own branch, then
merged into `develop` one at a time.

```
main ── develop ──┬── persona/T01-karen-whitfield
                  ├── persona/T02-doug-henley
                  ├── …
                  └── persona/E07-brittany-sloane
```

## Branches

| Branch | Purpose |
|---|---|
| `main` | What reviewers see. Changes only when the owner approves. |
| `develop` | Integration branch. Persona branches are merged here. |
| `persona/<ID>-<name>` | One agent's work for one persona. 20 in total. |

Each persona branch equals `develop` plus one file, `agents/briefs/<ID>.md`.
An agent reads `agents/RULES.md` and its own brief, and nothing else.

## 1. Start an agent

Agents need to reach Groq, Gemini and placidway.com, so they run on a machine
that can: the owner's computer, not the cloud session that prepared this repo.

```bash
cp .env.example .env          # once, in the main checkout; add the two API keys
scripts/persona_worktree.sh T01
```

The script makes a separate working folder for that persona's branch, copies
`.env` into it with the persona's port, and prints the prompt to give the
agent. Start a coding agent in that folder and paste the prompt.

Every persona has its own port (8101 to 8120), so several can run at once.
The free-tier keys are shared, so start a few at a time, not all 20.

## 2. Merge into develop, one branch at a time

For each finished branch, in ID order:

1. Read `notes/<ID>.md` on the branch.
2. Confirm the agent left the test suite alone:
   `git diff develop...persona/<branch> --stat -- tests personas botsuite`
   must print nothing.
3. Search the bot code for copied reference replies or exact-match lookups of
   the scripted messages.
4. `git checkout develop && git merge --no-ff persona/<branch>` and resolve
   conflicts. The first merge brings in a whole bot; every later one has to be
   folded into it, not placed beside it.
5. Run `pytest tests/test_suite_selfcheck.py`, then that persona and every
   persona already merged with `--runs 1`. A merge is done when none of them
   has regressed.

## 3. Clean up develop

- One ingestion pipeline, one index, one retriever, one LLM client, one prompt.
  Delete duplicates.
- Decide the disputed checks listed in the notes files; change
  `botsuite/phrases.yaml` or `botsuite/facts.yaml` only where the bot was
  right.
- Remove dead code and unused dependencies. Check no key is in the history.

## 4. Final test on develop

```bash
pytest                 # all 20 personas, 3 runs each, with latency and budget
pytest --run-abuse -k E06
```

## 5. Release

After the owner approves, merge `develop` into `main` and push. Decide then
whether `agents/` and `notes/` stay in the repository.
