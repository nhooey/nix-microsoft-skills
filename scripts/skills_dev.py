#!/usr/bin/env python3
"""
skills-dev: nix-microsoft-skills' own commands, as one tool.

Usage:
  skills-dev [--dry-run] build [SKILL ...]
  skills-dev [--dry-run] test [--verbose]
  skills-dev [--dry-run] bump [--apply]

Commands:
  build   Build the named skills' packages, or every skill when none is named.
  test    Run the scripts' unit tests in scripts/tests.
  bump    Compare the pinned upstream revisions with GitHub HEAD; with
          --apply, rewrite them, one commit per upstream repo.

Every command runs from the root of the clone it is started in. With
--dry-run it prints the commands it would run and runs nothing.

Exit status: 0 on success, 2 on bad usage, otherwise the status of the
first command that failed (1 when not inside a clone).
"""

import argparse
import shlex
import subprocess
import sys

PACKAGE_PREFIX = "agent-skill-nhooey-microsoft-"
ALL_PACKAGE = "default"


def package_attr(skill):
    """The flake attribute of a skill's package, given its bare name."""
    return skill if skill.startswith(PACKAGE_PREFIX) else PACKAGE_PREFIX + skill


def build_plan(skills):
    return (
        ("nix", "build", "--no-link", "--print-build-logs")
        + tuple(f".#{attr}" for attr in (tuple(map(package_attr, skills)) or (ALL_PACKAGE,))),
    )


def test_plan(verbose):
    return (
        ("python3", "-m", "unittest", "discover", "--start-directory", "scripts/tests")
        + (("--verbose",) if verbose else ()),
    )


def bump_plan(apply):
    return (("nix", "run", ".#bump") + (("--", "--apply") if apply else ()),)


def plan(args):
    """The commands one parsed invocation runs, in order."""
    match args.command:
        case "build":
            return build_plan(tuple(args.skills))
        case "test":
            return test_plan(args.verbose)
        case "bump":
            return bump_plan(args.apply)


def parser():
    top = argparse.ArgumentParser(
        prog="skills-dev",
        description="nix-microsoft-skills' own commands: build, test and bump.",
        epilog="Example: skills-dev --dry-run bump --apply",
    )
    top.add_argument(
        "--dry-run",
        action="store_true",
        help="print the commands instead of running them",
    )
    commands = top.add_subparsers(dest="command", required=True, metavar="COMMAND")

    build = commands.add_parser(
        "build",
        help="build skill packages",
        description="Build the named skills' packages, or every skill when none is named.",
        epilog="Example: skills-dev build dotnet-xunit avalonia-dev-review",
    )
    build.add_argument(
        "skills",
        nargs="*",
        metavar="SKILL",
        help=f"skill name, with or without the {PACKAGE_PREFIX} prefix",
    )

    test = commands.add_parser(
        "test",
        help="run the scripts' unit tests",
        description="Run the unit tests in scripts/tests with unittest.",
        epilog="Example: skills-dev test --verbose",
    )
    test.add_argument(
        "--verbose", action="store_true", help="name each test as it runs"
    )

    bump = commands.add_parser(
        "bump",
        help="compare pinned upstream revisions with GitHub",
        description=(
            "Compare each pinned upstream revision in pins.nix with "
            "GitHub HEAD. With --apply, rewrite the behind ones, one commit "
            "per upstream repo."
        ),
        epilog="Example: skills-dev bump --apply",
    )
    bump.add_argument(
        "--apply",
        action="store_true",
        help="rewrite the pins and commit, one commit per upstream repo",
    )
    return top


def repo_root():
    found = subprocess.run(
        ("git", "rev-parse", "--show-toplevel"),
        capture_output=True,
        text=True,
        check=False,
    )
    return found.stdout.strip() if found.returncode == 0 else None


def run_all(commands, cwd):
    """Run each command in turn; return the first non-zero status, or 0."""
    return next(
        (
            status
            for status in (subprocess.run(c, cwd=cwd, check=False).returncode for c in commands)
            if status != 0
        ),
        0,
    )


def main(argv=None):
    args = parser().parse_args(argv)
    commands = plan(args)
    if args.dry_run:
        print("\n".join(shlex.join(c) for c in commands))
        return 0
    root = repo_root()
    if root is None:
        print("skills-dev must run inside a clone of nix-microsoft-skills", file=sys.stderr)
        return 1
    return run_all(commands, root)


if __name__ == "__main__":
    sys.exit(main())
