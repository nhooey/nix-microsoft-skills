import re
import sys
import tempfile
import unittest
from contextlib import redirect_stderr
from io import StringIO
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rewrite_pin import RewriteFailed, main, rewrite_pin  # noqa: E402

OLD_REV = "a" * 40
NEW_REV = "b" * 40
OLD_HASH = "sha256-old="
NEW_HASH = "sha256-new="

# Two repos sharing a rev and hash, and a key that is a suffix of another.
PINS = f"""{{
  repos = {{
    first = {{
      owner = "o";
      repo = "first";
      rev = "{OLD_REV}";
      hash = "{OLD_HASH}";
      defaultBranch = "main";
    }};
    second = {{
      owner = "o";
      repo = "second";
      rev = "{OLD_REV}";
      hash = "{OLD_HASH}";
      defaultBranch = "main";
    }};
    other-first = {{
      owner = "o";
      repo = "other-first";
      rev = "{OLD_REV}";
      hash = "{OLD_HASH}";
      defaultBranch = "main";
    }};
  }};
  skills = {{ }};
}}
"""

PINS_FILE = Path(__file__).resolve().parents[2] / "skills" / "default.nix"


def block(src, key):
    return re.search(r"(?m)^    " + re.escape(key) + r" = \{.*?^    \};", src, re.DOTALL)[0]


class RewritePin(unittest.TestCase):
    def test_rewrites_rev_and_hash_of_named_block_only(self):
        new = rewrite_pin(PINS, "second", OLD_REV, NEW_REV, OLD_HASH, NEW_HASH)
        self.assertIn(f'rev = "{NEW_REV}";\n      hash = "{NEW_HASH}";', block(new, "second"))
        self.assertEqual(block(new, "first"), block(PINS, "first"))
        self.assertEqual(block(new, "other-first"), block(PINS, "other-first"))

    def test_changes_nothing_but_those_two_values(self):
        new = rewrite_pin(PINS, "second", OLD_REV, NEW_REV, OLD_HASH, NEW_HASH)
        self.assertEqual(new.replace(NEW_REV, OLD_REV).replace(NEW_HASH, OLD_HASH), PINS)
        self.assertEqual((new.count(NEW_REV), new.count(NEW_HASH)), (1, 1))

    def test_key_does_not_match_inside_a_longer_key(self):
        new = rewrite_pin(PINS, "first", OLD_REV, NEW_REV, OLD_HASH, NEW_HASH)
        self.assertIn(NEW_REV, block(new, "first"))
        self.assertEqual(block(new, "other-first"), block(PINS, "other-first"))

    def test_stale_rev_fails(self):
        self.assertEqual(
            rewrite_pin(PINS, "first", "c" * 40, NEW_REV, OLD_HASH, NEW_HASH),
            RewriteFailed("rewrite failed for first: matched 0 times"),
        )

    def test_stale_hash_fails(self):
        self.assertEqual(
            rewrite_pin(PINS, "first", OLD_REV, NEW_REV, "sha256-stale=", NEW_HASH),
            RewriteFailed("rewrite failed for first: matched 0 times"),
        )

    def test_key_matching_two_blocks_fails(self):
        doubled = PINS.replace("  skills = {", block(PINS, "first") + "\n  skills = {")
        self.assertEqual(
            rewrite_pin(doubled, "first", OLD_REV, NEW_REV, OLD_HASH, NEW_HASH),
            RewriteFailed("rewrite failed for first: matched 2 times"),
        )

    def test_unknown_key_fails(self):
        self.assertIsInstance(
            rewrite_pin(PINS, "missing", OLD_REV, NEW_REV, OLD_HASH, NEW_HASH),
            RewriteFailed,
        )

    def test_every_repo_in_the_real_pins_file_rewrites_in_place(self):
        src = PINS_FILE.read_text()
        repos = re.findall(
            r'(?m)^    ([\w-]+) = \{\n(?:.*\n)*?\s*rev = "(\w+)";\n\s*hash = "([^"]+)";', src
        )
        self.assertEqual(len(repos), 3)
        for key, rev, hash_ in repos:
            with self.subTest(key=key):
                new = rewrite_pin(src, key, rev, NEW_REV, hash_, NEW_HASH)
                self.assertIn(f'rev = "{NEW_REV}";', block(new, key))
                self.assertEqual(new.replace(NEW_REV, rev).replace(NEW_HASH, hash_), src)


class MainRewritesFile(unittest.TestCase):
    """The shell: writes the file on success, leaves it alone on failure."""

    def run_main(self, *args):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp, "default.nix")
            path.write_text(PINS)
            with redirect_stderr(StringIO()) as err:
                code = main([str(path), *args])
            return code, path.read_text(), err.getvalue()

    def test_success_writes_new_pins(self):
        code, text, _ = self.run_main("first", OLD_REV, NEW_REV, OLD_HASH, NEW_HASH)
        self.assertEqual(code, 0)
        self.assertEqual(text, rewrite_pin(PINS, "first", OLD_REV, NEW_REV, OLD_HASH, NEW_HASH))

    def test_failure_leaves_file_and_reports(self):
        code, text, err = self.run_main("missing", OLD_REV, NEW_REV, OLD_HASH, NEW_HASH)
        self.assertEqual((code, text), (1, PINS))
        self.assertEqual(err, "rewrite failed for missing: matched 0 times\n")


if __name__ == "__main__":
    unittest.main()
