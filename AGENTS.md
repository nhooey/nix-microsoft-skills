# Agent instructions for nix-microsoft-skills

A Nix flake packaging ten community Claude Code skills for the
Microsoft / .NET stack: `agent-skill-nhooey-microsoft-<skill>` per
skill, plus `agent-skills-nhooey-microsoft-all` (the default). It builds on
`nhooey/agent-skill-flake` and is meant for inclusion in
`nhooey/skillspkgs`; installing the skills is the consumer's job, not
this repository's.

- `skills/default.nix` holds every upstream pin, in one attrset.
- `scripts/check_skills.py` validates the built skills for the
  `skills-valid` check; `scripts/bump.sh` backs `nix run .#bump`.
- `scripts/tests/` holds `unittest` tests of the scripts' pure
  functions. `nix flake check` runs them (`scripts-tests`); run them
  directly with `python3 -m unittest discover -s scripts/tests`.
- `skills-devshell/` is a separate sub-flake holding the skills the dev
  shell installs into `.agents/skills/`; it is never a root input.

## Build and test

- `nix develop` enters the dev shell and installs its skills.
- `nix flake check` builds every skill, validates them (`skills-valid`),
  runs the scripts' unit tests (`scripts-tests`) and checks formatting
  (`treefmt`). It must pass before a change merges.
- `nix fmt` formats the tree.
- `nix run .#bump` compares the pinned upstream revisions with GitHub;
  `nix run .#bump -- --apply` bumps them, one commit per upstream repo.
