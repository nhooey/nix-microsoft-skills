#!/usr/bin/env python3
"""
Rewrite one repo's rev and hash in pins.nix, in place.

Usage:
  rewrite_pin.py PINS_FILE KEY OLD_REV NEW_REV OLD_HASH NEW_HASH

The pins file's shape per repo block is:

  <key> = {
    owner = "...";
    repo = "...";
    rev = "<sha>";
    hash = "sha256-...";
    ...
  };

Only the rev and hash lines inside the `<key> = { ... }` block change, so a
pin elsewhere that shares the old rev or hash is left alone. Exits non-zero,
leaving the file untouched, unless exactly that block matches.
"""

import re
import sys
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RewriteFailed:
    reason: str


def block_pattern(key, old_rev, old_hash):
    return re.compile(
        r"((?<![\w-])" + re.escape(key) + r"\s*=\s*\{[^}]*?)"
        + r'(rev\s*=\s*")' + re.escape(old_rev) + r'(")'
        + r"([^}]*?)"
        + r'(hash\s*=\s*")' + re.escape(old_hash) + r'(")',
        re.DOTALL,
    )


def rewrite_pin(src, key, old_rev, new_rev, old_hash, new_hash):
    """`src` with KEY's rev and hash replaced, or RewriteFailed."""
    matches = block_pattern(key, old_rev, old_hash).findall(src)
    if len(matches) != 1:
        return RewriteFailed(f"rewrite failed for {key}: matched {len(matches)} times")
    return block_pattern(key, old_rev, old_hash).sub(
        lambda m: f"{m[1]}{m[2]}{new_rev}{m[3]}{m[4]}{m[5]}{new_hash}{m[6]}",
        src,
        count=1,
    )


def main(argv):
    if len(argv) != 6:
        print(__doc__, file=sys.stderr)
        return 2
    path, *args = argv
    with open(path, encoding="utf-8") as fh:
        result = rewrite_pin(fh.read(), *args)
    match result:
        case RewriteFailed(reason):
            print(reason, file=sys.stderr)
            return 1
        case str(new_src):
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(new_src)
            return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
