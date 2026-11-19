import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from check_skills import (  # noqa: E402
    Invalid,
    Parsed,
    from_json,
    frontmatter_block,
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


def errors(name, text):
    return skill_errors(name, parse_frontmatter(text))


class FrontmatterBlock(unittest.TestCase):
    def test_text_between_fences(self):
        self.assertEqual(frontmatter_block(skill_md()), "name: demo\ndescription: Does a thing.\n")

    def test_none_without_fences(self):
        self.assertIsNone(frontmatter_block("# Just a heading\n"))

    def test_none_when_unclosed(self):
        self.assertIsNone(frontmatter_block("---\nname: demo\n"))


class FromJson(unittest.TestCase):
    def test_mapping(self):
        self.assertEqual(dict(from_json('{"name": "demo"}').fields), {"name": "demo"})

    def test_null_is_empty(self):
        self.assertEqual(dict(from_json("null").fields), {})

    def test_scalar_is_invalid(self):
        self.assertEqual(from_json('"text"').problems, ("not a mapping of keys to values: 'text'",))

    def test_duplicate_key_is_invalid(self):
        self.assertEqual(
            from_json('{"name": "a", "name": "b"}').problems, ("duplicate key `name`",)
        )


class ParseFrontmatterAsYaml(unittest.TestCase):
    def test_plain_scalars(self):
        self.assertEqual(fields(skill_md()), {"name": "demo", "description": "Does a thing."})

    def test_quoted_name(self):
        self.assertEqual(fields('---\nname: "demo"\ndescription: d\n---\n')["name"], "demo")

    def test_double_quoted_scalar_with_trailing_comment(self):
        text = '---\nname: demo\ndescription: "Use it" # why\n---\n'
        self.assertEqual(fields(text)["description"], "Use it")

    def test_single_quoted_scalar_with_trailing_comment(self):
        text = "---\nname: 'demo' # the name\ndescription: 'Use it' # why\n---\n"
        self.assertEqual(fields(text), {"name": "demo", "description": "Use it"})

    def test_yaml_escape_json_lacks(self):
        text = '---\nname: demo\ndescription: "caf\\xe9 tab\\ttab"\n---\n'
        self.assertEqual(fields(text)["description"], "café tab\ttab")

    def test_null_description(self):
        self.assertIsNone(fields("---\nname: demo\ndescription: null\n---\n")["description"])

    def test_tilde_description(self):
        self.assertIsNone(fields("---\nname: demo\ndescription: ~\n---\n")["description"])

    def test_no_frontmatter(self):
        self.assertEqual(
            problems("# Just a heading\n"), ("no frontmatter block between `---` lines",)
        )

    def test_invalid_yaml(self):
        (problem,) = problems("---\nname: demo\ndescription: Use for: things\n---\n")
        self.assertTrue(problem.startswith("not valid YAML: "), problem)

    def test_duplicate_key(self):
        self.assertEqual(
            problems("---\nname: a\nname: b\ndescription: d\n---\n"), ("duplicate key `name`",)
        )


class SkillErrors(unittest.TestCase):
    def test_valid_skill_has_no_errors(self):
        self.assertEqual(errors("demo", skill_md()), ())

    def test_missing_skill_md(self):
        self.assertEqual(skill_errors("demo", None), ("demo: SKILL.md missing",))

    def test_name_mismatch(self):
        self.assertEqual(
            errors("demo", skill_md(name="other")),
            ("demo: frontmatter name='other' != directory name",),
        )

    def test_missing_name(self):
        self.assertEqual(
            errors("demo", "---\ndescription: d\n---\n"),
            ("demo: frontmatter missing `name:`",),
        )

    def test_missing_description(self):
        self.assertEqual(
            errors("demo", "---\nname: demo\n---\n"),
            ("demo: frontmatter missing `description:`",),
        )

    def test_null_description(self):
        self.assertEqual(
            errors("demo", "---\nname: demo\ndescription: ~\n---\n"),
            ("demo: frontmatter `description:` is not a non-empty string (None)",),
        )

    def test_number_name(self):
        self.assertEqual(
            errors("2024", "---\nname: 2024\ndescription: d\n---\n"),
            ("2024: frontmatter `name:` is not a non-empty string (2024)",),
        )

    def test_nested_name(self):
        (error,) = errors("demo", "---\nname:\n  first: demo\ndescription: d\n---\n")
        self.assertIn("`name:` is not a non-empty string", error)

    def test_frontmatter_problems_are_prefixed_with_skill(self):
        self.assertEqual(
            errors("demo", "no frontmatter"),
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
        skills = {
            "a": Parsed({"name": "a", "description": "d"}),
            "b": None,
            "c": Parsed({"name": "x", "description": "d"}),
        }
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
