#!/usr/bin/env python3
"""Assemble the static site.

The site is `web/` plus the `app` package dropped in beside it, so the browser
imports exactly the same geometry code that runs on a workstation. Nothing is
compiled, transpiled or bundled: the output is the input, copied.

    python3 tools/build_site.py [outdir]             # default: _site
    python3 tools/build_site.py --serve [--port N]   # and serve it

Serving matters: PyScript fetches its modules and wheels, and `file://`
blocks that, so the site has to come over http even locally.
"""

from __future__ import annotations

import argparse
import functools
import http.server
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WEB = ROOT / "web"
APP = ROOT / "app"


def build(out: Path) -> Path:
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)

    shutil.copytree(WEB, out, dirs_exist_ok=True)
    shutil.copytree(
        APP,
        out / "app",
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "static"),
    )

    # GitHub Pages runs everything through Jekyll unless told not to, and
    # Jekyll drops directories that start with an underscore.
    (out / ".nojekyll").touch()

    return out


class NoCacheHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    """Disable caching during local development/testing so reloads get fresh files."""

    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        super().end_headers()


def serve(root: Path, port: int) -> None:
    handler = functools.partial(NoCacheHTTPRequestHandler, directory=str(root))
    with http.server.ThreadingHTTPServer(("127.0.0.1", port), handler) as httpd:
        print(f"serving http://127.0.0.1:{port}/  (ctrl-c to stop)")
        httpd.serve_forever()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("outdir", nargs="?", default=str(ROOT / "_site"))
    parser.add_argument("--serve", action="store_true", help="serve the result")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()

    built = build(Path(args.outdir).resolve())
    files = sum(1 for p in built.rglob("*") if p.is_file())
    print(f"built {built} ({files} files)")

    if args.serve:
        serve(built, args.port)
