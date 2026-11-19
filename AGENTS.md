# Agent instructions for nix-microsoft-skills

A Nix flake packaging ten community Claude Code skills for the
Microsoft / .NET stack: `agent-skill-nhooey-microsoft-<skill>` per
skill, plus `agent-skills-nhooey-microsoft-all` (the default). It builds on
`nhooey/agent-skill-flake` and is meant for inclusion in
`nhooey/skillspkgs`; installing the skills is the consumer's job, not
this repository's.

- `pins.nix` holds every upstream pin, in one attrset.
- `scripts/skills_dev.py` is `skills-dev`, the dev shell's tool for
  this repository's own commands.
- `scripts/check_skills.py` validates the built skills for the
  `skills-valid` check; `scripts/bump.sh` backs `nix run .#bump` and
  rewrites pins through `scripts/rewrite_pin.py`.
- `scripts/tests/` holds `unittest` tests of those scripts' pure
  functions. `nix flake check` runs them (`scripts-tests`).
- `skills-devshell/` is a separate sub-flake holding the skills the dev
  shell installs into `.agents/skills/`; it is never a root input.

## Build and test

`nix develop` enters the dev shell and installs its skills; `menu`
lists its commands.

- `check` runs `nix flake check`: it builds every skill, validates them
  (`skills-valid`), runs the scripts' unit tests (`scripts-tests`) and
  checks formatting (`treefmt`). It must pass before a change merges.
- `fmt` formats the tree.
- `skills-dev build [SKILL ...]` builds the named skills, or all of them.
- `skills-dev test` runs the scripts' unit tests outside the sandbox.
- `skills-dev bump` compares the pinned upstream revisions with GitHub;
  `skills-dev bump --apply` bumps them, one commit per upstream repo.
- `skills-dev --dry-run <command>` prints what a command would run.
