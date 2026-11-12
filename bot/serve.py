"""Run the bot locally:  python -m bot.serve --port 8101  (endpoint: /api/chat)."""
from __future__ import annotations

import argparse
from http.server import ThreadingHTTPServer

from .retrieval import load_index
from .web import ChatHandler


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8101)
    args = parser.parse_args()
    passages = len(load_index().passages)       # fail now, not on the first request, if the index is missing
    print(f"[bot] {passages} passages loaded; listening on http://127.0.0.1:{args.port}/api/chat", flush=True)
    ThreadingHTTPServer(("127.0.0.1", args.port), ChatHandler).serve_forever()


if __name__ == "__main__":
    main()
