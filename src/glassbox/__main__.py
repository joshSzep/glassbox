"""Module entry point for `python -m glassbox`."""

import sys

from glassbox.cli import main

if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
