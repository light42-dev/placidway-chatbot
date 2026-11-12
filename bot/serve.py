"""Run the bot locally:  python -m bot.serve --port 8101

Serves the chat page at / and the chat endpoint at /api/chat. On Vercel the
page comes from public/ and the endpoint from api/chat.py instead.
"""
from __future__ import annotations

import argparse
from http.server import ThreadingHTTPServer

from .config import ROOT
from .retrieval import load_index
from .web import ChatHandler

CHAT_PAGE = ROOT / "public" / "index.html"


class LocalHandler(ChatHandler):
    """The chat endpoint, plus the chat page for GET /."""

    def do_GET(self) -> None:
        if self.path.split("?")[0] not in ("/", "/index.html"):
            self.send_error(404)
            return
        page = CHAT_PAGE.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(page)))
        self.end_headers()
        self.wfile.write(page)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8101)
    args = parser.parse_args()
    passages = len(load_index().passages)       # fail now, not on the first request, if the index is missing
    print(f"[bot] {passages} passages loaded; chat page at http://127.0.0.1:{args.port}/", flush=True)
    ThreadingHTTPServer(("127.0.0.1", args.port), LocalHandler).serve_forever()


if __name__ == "__main__":
    main()
