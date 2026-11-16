import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from check_skills import (  # noqa: E402
    NON_SCALAR,
    Invalid,
    Parsed,
    listing_errors,
    main,
    parse_expected,
    parse_frontmatter,
    skill_errors,
    validate,
)


def skill_md(name="demo", description="Does a thing."):
    return f"---\nname: {name}\ndescription: {description}\n---\n\n# Body\n"


def fields(text):
    result = parse_frontmatter(text)
    assert isinstance(result, Parsed), result
    return dict(result.fields)


def problems(text):
    result = parse_frontmatter(text)
    assert isinstance(result, Invalid), result
    return result.problems


class ParseFrontmatterScalars(unittest.TestCase):
    def test_plain_scalars(self):
        self.assertEqual(
            fields(skill_md()), {"name": "demo", "description": "Does a thing."}
        )

    def test_double_quoted_scalar_with_escapes(self):
        text = '---\nname: "demo"\ndescription: "Say \\"hi\\": now"\n---\n'
        self.assertEqual(fields(text)["description"], 'Say "hi": now')

    def test_double_quoted_scalar_with_yaml_only_escapes(self):
        text = '---\nname: demo\ndescription: "\\x41\\_B\\e\\U0001F600 \\/"\n---\n'
        self.assertEqual(fields(text)["description"], "A B\x1b\U0001F600 /")

    def test_double_quoted_scalar_with_literal_tab(self):
        text = '---\nname: demo\ndescription: "a\tb"\n---\n'
        self.assertEqual(fields(text)["description"], "a\tb")

    def test_single_quoted_scalar_with_doubled_quote(self):
        text = "---\nname: 'demo'\ndescription: 'it''s: fine'\n---\n"
        self.assertEqual(fields(text)["description"], "it's: fine")

    def test_plain_scalar_continued_on_indented_lines_folds_to_spaces(self):
        text = "---\nname: demo\ndescription: one\n  two\n  three\n---\n"
        self.assertEqual(fields(text)["description"], "one two three")

    def test_trailing_comment_is_dropped_from_plain_scalar(self):
        text = "---\nname: demo # the name\ndescription: x\n---\n"
        self.assertEqual(fields(text)["name"], "demo")

    def test_folded_block_scalar_clips_to_one_newline(self):
        text = "---\nname: demo\ndescription: >\n  one\n  two\n\n  three\n---\n"
        self.assertEqual(fields(text)["description"], "one two\nthree\n")

    def test_literal_block_scalar_keeps_newlines(self):
        text = "---\nname: demo\ndescription: |\n  one\n  two\n---\n"
        self.assertEqual(fields(text)["description"], "one\ntwo\n")

    def test_strip_chomping_drops_final_newline(self):
        text = "---\nname: demo\ndescription: >-\n  one\n  two\n---\n"
        self.assertEqual(fields(text)["description"], "one two")

    def test_nested_mapping_is_non_scalar(self):
        text = "---\nname: demo\nmetadata:\n  type: x\ndescription: d\n---\n"
        self.assertIs(fields(text)["metadata"], NON_SCALAR)

    def test_flow_sequence_is_non_scalar(self):
        text = "---\nname: demo\ndescription: d\ntags: [a, b]\n---\n"
        self.assertIs(fields(text)["tags"], NON_SCALAR)

    def test_empty_value_is_none(self):
        self.assertIsNone(fields("---\nname:\ndescription: d\n---\n")["name"])

    def test_comment_lines_are_skipped(self):
        text = "---\n# leading\nname: demo\n# between\ndescription: d\n---\n"
        self.assertEqual(fields(text), {"name": "demo", "description": "d"})

    def test_trailing_comment_is_dropped_from_quoted_scalars(self):
        text = "---\nname: \"demo\" # the name\ndescription: 'd' # what\n---\n"
        self.assertEqual(fields(text), {"name": "demo", "description": "d"})

    def test_comment_line_after_quoted_scalar_is_skipped(self):
        text = '---\ndescription: "d"\n# between\nname: \'demo\'\n# after\n---\n'
        self.assertEqual(fields(text), {"name": "demo", "description": "d"})

    def test_comment_alone_after_key_is_an_empty_value(self):
        self.assertIsNone(fields("---\nname: demo\ndescription: # none\n---\n")["description"])

    def test_space_before_the_colon(self):
        text = "---\nname : demo\ndescription:\td\n---\n"
        self.assertEqual(fields(text), {"name": "demo", "description": "d"})

    def test_crlf_line_endings(self):
        text = "---\r\nname: demo\r\ndescription: one\r\n  two\r\n---\r\n\r\n# Body\r\n"
        self.assertEqual(fields(text), {"name": "demo", "description": "one two"})


class ParseFrontmatterRejects(unittest.TestCase):
    def test_no_frontmatter(self):
        self.assertEqual(
            problems("# Just a heading\n"), ("no frontmatter block between `---` lines",)
        )

    def test_unclosed_frontmatter(self):
        self.assertEqual(
            problems("---\nname: demo\n"), ("no frontmatter block between `---` lines",)
        )

    def test_line_without_key(self):
        (problem,) = problems("---\nname: demo\njust words\n---\n")
        self.assertIn("line 3: not a `key: value` line", problem)

    def test_plain_scalar_holding_colon_space(self):
        (problem,) = problems("---\nname: demo\ndescription: Use for: things\n---\n")
        self.assertIn("line 3: plain scalar contains ': '", problem)

    def test_unterminated_double_quote(self):
        (problem,) = problems('---\nname: "demo\ndescription: d\n---\n')
        self.assertIn("line 2: double-quoted scalar doesn't parse", problem)

    def test_unknown_double_quoted_escape(self):
        (problem,) = problems('---\nname: demo\ndescription: "a\\qb"\n---\n')
        self.assertIn("line 3: double-quoted scalar doesn't parse", problem)

    def test_escape_beyond_unicode(self):
        (problem,) = problems('---\nname: demo\ndescription: "\\UFFFFFFFF"\n---\n')
        self.assertIn("line 3: double-quoted scalar doesn't parse", problem)

    def test_short_hex_escape(self):
        (problem,) = problems('---\nname: demo\ndescription: "a\\x4"\n---\n')
        self.assertIn("line 3: double-quoted scalar doesn't parse", problem)

    def test_unterminated_single_quote(self):
        (problem,) = problems("---\nname: 'demo\ndescription: d\n---\n")
        self.assertIn("line 2: single-quoted scalar doesn't parse", problem)

    def test_duplicate_key(self):
        (problem,) = problems("---\nname: a\nname: b\ndescription: d\n---\n")
        self.assertEqual(problem, "line 3: duplicate key `name`")

    def test_alias(self):
        (problem,) = problems("---\nname: *anchor\ndescription: d\n---\n")
        self.assertIn("anchors, aliases and tags aren't supported", problem)

    def test_reserved_indicator(self):
        (problem,) = problems("---\nname: `demo`\ndescription: d\n---\n")
        self.assertIn("is reserved", problem)

    def test_indented_line_before_any_key(self):
        (problem,) = problems("---\n  name: demo\ndescription: d\n---\n")
        self.assertEqual(problem, "line 2: indented line before any key")


class SkillErrors(unittest.TestCase):
    def test_valid_skill_has_no_errors(self):
        self.assertEqual(skill_errors("demo", skill_md()), ())

    def test_missing_skill_md(self):
        self.assertEqual(skill_errors("demo", None), ("demo: SKILL.md missing",))

    def test_name_mismatch(self):
        self.assertEqual(
            skill_errors("demo", skill_md(name="other")),
            ("demo: frontmatter name='other' != directory name",),
        )

    def test_block_scalar_name_does_not_match_directory(self):
        text = "---\nname: |\n  demo\ndescription: d\n---\n"
        self.assertEqual(
            skill_errors("demo", text),
            ("demo: frontmatter name='demo\\n' != directory name",),
        )

    def test_missing_name(self):
        self.assertEqual(
            skill_errors("demo", "---\ndescription: d\n---\n"),
            ("demo: frontmatter missing `name:`",),
        )

    def test_missing_description(self):
        self.assertEqual(
            skill_errors("demo", "---\nname: demo\n---\n"),
            ("demo: frontmatter missing `description:`",),
        )

    def test_empty_description(self):
        (error,) = skill_errors("demo", "---\nname: demo\ndescription:\n---\n")
        self.assertIn("`description:` is not a non-empty string", error)

    def test_description_that_is_only_a_comment(self):
        (problem,) = skill_errors("demo", "---\nname: demo\ndescription: # todo\n---\n")
        self.assertIn("`description:` is not a non-empty string", problem)

    def test_nested_name(self):
        text = "---\nname:\n  first: demo\ndescription: d\n---\n"
        (error,) = skill_errors("demo", text)
        self.assertIn("`name:` is not a non-empty string", error)

    def test_frontmatter_problems_are_prefixed_with_skill(self):
        self.assertEqual(
            skill_errors("demo", "no frontmatter"),
            ("demo: frontmatter: no frontmatter block between `---` lines",),
        )


class ListingErrors(unittest.TestCase):
    def test_matching_listing(self):
        self.assertEqual(listing_errors(("a", "b"), ("a", "b"), 2), ())

    def test_count_mismatch(self):
        self.assertEqual(
            listing_errors(("a", "b"), ("a", "b"), 3),
            ("directory count: expected 3, got 2 (['a', 'b'])",),
        )

    def test_missing_and_unexpected(self):
        self.assertEqual(
            listing_errors(("a", "c"), ("a", "b"), 2),
            ("missing skills: ['b']", "unexpected skills: ['c']"),
        )


class Validate(unittest.TestCase):
    def test_collects_listing_and_skill_errors(self):
        skills = {"a": skill_md("a"), "b": None, "c": skill_md("x")}
        self.assertEqual(
            validate(skills, ("a", "b"), 2),
            (
                "directory count: expected 2, got 3 (['a', 'b', 'c'])",
                "unexpected skills: ['c']",
                "b: SKILL.md missing",
                "c: frontmatter name='x' != directory name",
            ),
        )

    def test_parse_expected_sorts_and_drops_blank_lines(self):
        self.assertEqual(parse_expected("b\n\na\n  \n"), ("a", "b"))


class MainOverDirectory(unittest.TestCase):
    """The shell: reads a real directory tree and returns an exit code."""

    def run_main(self, tree, expected):
        with tempfile.TemporaryDirectory() as tmp:
            share = Path(tmp, "share")
            share.mkdir()
            for name, text in tree.items():
                Path(share, name).mkdir()
                if text is not None:
                    Path(share, name, "SKILL.md").write_text(text)
            Path(share, "stray-file").write_text("not a skill directory")
            listing = Path(tmp, "expected")
            listing.write_text("\n".join(expected) + "\n")
            out, err = StringIO(), StringIO()
            with redirect_stdout(out), redirect_stderr(err):
                code = main([str(share), str(len(expected)), str(listing)])
            return code, out.getvalue(), err.getvalue()

    def test_valid_tree_exits_zero(self):
        code, out, _ = self.run_main({"a": skill_md("a"), "b": skill_md("b")}, ["b", "a"])
        self.assertEqual((code, out), (0, "OK: 2 skills validated\n"))

    def test_invalid_tree_exits_one_and_reports_each_error(self):
        code, _, err = self.run_main({"a": skill_md("a"), "b": None}, ["a", "b"])
        self.assertEqual((code, err), (1, "FAIL: b: SKILL.md missing\n"))

    def test_wrong_argument_count_exits_two(self):
        with redirect_stderr(StringIO()):
            self.assertEqual(main([]), 2)


if __name__ == "__main__":
    unittest.main()
