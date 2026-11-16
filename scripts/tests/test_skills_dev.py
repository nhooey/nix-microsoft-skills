import sys
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from skills_dev import main, package_attr, parser, plan  # noqa: E402


def plan_of(*argv):
    return plan(parser().parse_args(argv))


def exit_status(*argv):
    out, err = StringIO(), StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        try:
            return main(list(argv)), out.getvalue()
        except SystemExit as stop:
            return stop.code, out.getvalue()


class PackageAttrTest(unittest.TestCase):
    def test_adds_the_prefix_to_a_bare_name(self):
        self.assertEqual(
            package_attr("dotnet-xunit"), "agent-skill-nhooey-microsoft-dotnet-xunit"
        )

    def test_keeps_a_name_that_has_the_prefix(self):
        self.assertEqual(
            package_attr("agent-skill-nhooey-microsoft-dotnet-xunit"),
            "agent-skill-nhooey-microsoft-dotnet-xunit",
        )


class PlanTest(unittest.TestCase):
    def test_build_without_skills_builds_the_default_package(self):
        self.assertEqual(
            plan_of("build"),
            (("nix", "build", "--no-link", "--print-build-logs", ".#default"),),
        )

    def test_build_names_each_skill_in_one_nix_build(self):
        self.assertEqual(
            plan_of("build", "dotnet-xunit", "avalonia-dev-review"),
            (
                (
                    "nix",
                    "build",
                    "--no-link",
                    "--print-build-logs",
                    ".#agent-skill-nhooey-microsoft-dotnet-xunit",
                    ".#agent-skill-nhooey-microsoft-avalonia-dev-review",
                ),
            ),
        )

    def test_test_discovers_the_scripts_tests(self):
        self.assertEqual(
            plan_of("test"),
            (
                (
                    "python3",
                    "-m",
                    "unittest",
                    "discover",
                    "--start-directory",
                    "scripts/tests",
                ),
            ),
        )

    def test_test_verbose_passes_verbose_to_unittest(self):
        self.assertEqual(plan_of("test", "--verbose")[0][-1], "--verbose")

    def test_bump_is_a_dry_run_by_default(self):
        self.assertEqual(plan_of("bump"), (("nix", "run", ".#bump"),))

    def test_bump_apply_passes_apply_to_the_app(self):
        self.assertEqual(
            plan_of("bump", "--apply"), (("nix", "run", ".#bump", "--", "--apply"),)
        )


class MainTest(unittest.TestCase):
    def test_dry_run_prints_the_commands_and_succeeds(self):
        self.assertEqual(
            exit_status("--dry-run", "bump", "--apply"),
            (0, "nix run '.#bump' -- --apply\n"),
        )

    def test_no_command_is_bad_usage(self):
        self.assertEqual(exit_status()[0], 2)

    def test_unknown_command_is_bad_usage(self):
        self.assertEqual(exit_status("deploy")[0], 2)

    def test_unknown_option_is_bad_usage(self):
        self.assertEqual(exit_status("bump", "--force")[0], 2)

    def test_help_lists_every_command(self):
        status, out = exit_status("--help")
        self.assertEqual(status, 0)
        for command in ("build", "test", "bump", "--dry-run"):
            self.assertIn(command, out)


if __name__ == "__main__":
    unittest.main()
