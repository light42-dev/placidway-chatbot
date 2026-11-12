#!/usr/bin/env bash
# Make a separate working folder for one persona branch and print the prompt
# to give its agent.
#
#   scripts/persona_worktree.sh T01
#
# Run it from the main checkout. The folder is created next to the repository,
# for example ../placidway-chatbot-T01.
set -euo pipefail

id="${1:?usage: scripts/persona_worktree.sh <persona ID, for example T01>}"
root="$(git rev-parse --show-toplevel)"
cd "$root"

git fetch --quiet origin || echo "warning: could not fetch from origin; using local branches" >&2

branch="$(git for-each-ref --format='%(refname:short)' \
          "refs/heads/persona/${id}-*" "refs/remotes/origin/persona/${id}-*" \
          | sed 's#^origin/##' | sort -u | head -n 1)"
if [ -z "$branch" ]; then
  echo "error: no branch named persona/${id}-* was found" >&2
  exit 1
fi

folder="$(dirname "$root")/$(basename "$root")-${id}"
if [ -e "$folder" ]; then
  echo "error: $folder already exists" >&2
  exit 1
fi
git worktree add --quiet "$folder" "$branch"

port="$(sed -n 's/^- \*\*Port:\*\* \([0-9]*\).*/\1/p' "$folder/agents/briefs/${id}.md")"
if [ -f "$root/.env" ]; then
  grep -v '^BOT_URL=' "$root/.env" > "$folder/.env"
else
  echo "warning: no .env in $root; add GROQ_API_KEY and GEMINI_API_KEY to $folder/.env" >&2
  : > "$folder/.env"
fi
echo "BOT_URL=http://127.0.0.1:${port}/api/chat" >> "$folder/.env"

cat <<EOF
Folder:  $folder
Branch:  $branch
Bot URL: http://127.0.0.1:${port}/api/chat

Start a coding agent in that folder and give it this prompt:

  You are on git branch ${branch}. Read agents/RULES.md and
  agents/briefs/${id}.md, then do exactly what they say. Read no other file
  under personas/ or agents/briefs/.
EOF
